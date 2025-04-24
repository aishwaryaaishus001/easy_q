from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from . models import Question, ClusteredQuestion
from collections import defaultdict
from collections import Counter
from itertools import product, combinations_with_replacement
from classifier.utils import predict_difficulty 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
import numpy as np
import json
import random
import traceback
from datetime import date



# Create your views here.
def home(request):
    return render(request, 'home.html')

def is_distribution_possible(distribution):
    """Check if it's even possible to form these values with 4,6,8,12."""
    allowed = [4, 6, 8, 12]
    for value in distribution.values():
        dp = [False] * (value + 1)
        dp[0] = True
        for i in range(1, value + 1):
            for a in allowed:
                if i - a >= 0 and dp[i - a]:
                    dp[i] = True
                    break
        if not dp[value]:
            return False
    return True

def generate_valid_marks(max_value):
    allowed = [4, 6, 8, 12]
    dp = [False] * (max_value + 1)
    dp[0] = True
    for i in range(1, max_value + 1):
        for a in allowed:
            if i - a >= 0 and dp[i - a]:
                dp[i] = True
                break
    return [i for i, valid in enumerate(dp) if valid]

def get_optimal_distribution(original_distribution, total_required=124):
    # Generate valid marks for each module (within reasonable limit)
    valid_options = {
        mod: generate_valid_marks(original_distribution[mod] + 12)
        for mod in original_distribution
    }

    min_deviation = float('inf')
    best_combo = None

    for combo in product(*valid_options.values()):
        if sum(combo) == total_required:
            deviation = sum(abs(combo[i] - original_distribution[i + 1]) for i in range(4))
            if deviation < min_deviation:
                min_deviation = deviation
                best_combo = combo

    if best_combo:
        return {i + 1: best_combo[i] for i in range(4)}
    return original_distribution  # fallback to original if nothing matches

def get_valid_combinations(target, marks=(4, 6, 8, 12)):
    results = []
    for r in range(1, target // min(marks) + 1):
        for combo in combinations_with_replacement(marks, r):
            if sum(combo) == target:
                results.append(combo)
    #print('valid combinations: ', results)            
    return results

def generate_question_paper(request):
    if request.method == 'POST':
        paper = request.POST.get('paper')
        module_limits = {
            1: int(request.POST.get('module1')),
            2: int(request.POST.get('module2')),
            3: int(request.POST.get('module3')),
            4: int(request.POST.get('module4')),
        }
        module_used = defaultdict(int)
        print('\n\nModule limits: ', module_limits, '\n\n')

        def can_use(q, marks):
            mod = q.module
            return module_used[mod] + marks <= module_limits[mod]
        
        def can_use_group(group, marks_list):
            """Check if a group of questions (with matching marks list) can be added."""
            temp_usage = defaultdict(int)
            for q, m in zip(group, marks_list):
                temp_usage[q.module] += m
            return all(module_used[mod] + temp_usage[mod] <= module_limits[mod] for mod in temp_usage)


        # Get all questions for the paper
        questions = ClusteredQuestion.objects.filter(paper=paper)

        easy_qs = list(questions.filter(difficulty="easy"))
        moderate_qs = list(questions.filter(difficulty="medium"))
        difficult_qs = list(questions.filter(difficulty="difficult"))

        # Shuffle for randomness
        random.shuffle(easy_qs)
        random.shuffle(moderate_qs)
        random.shuffle(difficult_qs)

        # ---------------- Section A: 6 questions × 4 marks ----------------
        sectionA = []
        for q in easy_qs + moderate_qs:
            if len(sectionA) < 6 and can_use(q, 4):
                sectionA.append(q)
                module_used[q.module] += 4

        # ---------------- Section B: 5 questions × 8 marks ----------------
        sectionB = []
        for q in difficult_qs + moderate_qs + easy_qs:
            if len(sectionB) < 5 and can_use(q, 8):
                sectionB.append(q)
                module_used[q.module] += 8

        # ---------------- Prepare available pools for Section C ----------------
        used_in_A_and_B = set(sectionA + sectionB)
        available_easy = [q for q in easy_qs if q not in used_in_A_and_B]
        available_moderate = [q for q in moderate_qs if q not in used_in_A_and_B]
        available_difficult = [q for q in difficult_qs if q not in used_in_A_and_B]

        random.shuffle(available_easy)
        random.shuffle(available_moderate)
        random.shuffle(available_difficult)        

        # ---------------- Section C: 5 questions × 12 marks ----------------
        sectionC = []
        # 3 Easy = 4+4+4 = 12
        if len(available_easy) >= 3:
            group = [available_easy.pop(), available_easy.pop(), available_easy.pop()]
            if can_use_group(group, [4, 4, 4]):
                sectionC.append(group)
                for q in group:
                    module_used[q.module] += 4
            else:
                # Return them back if not usable
                available_easy.extend(group)

        # 2 groups of (1 easy + 1 moderate)
        for _ in range(2):
            if len(available_easy) >= 1 and len(available_moderate) >= 1:
                group = [available_easy.pop(), available_moderate.pop()]
                if can_use_group(group, [4, 8]):
                    sectionC.append(group)
                    module_used[group[0].module] += 4
                    module_used[group[1].module] += 8
                else:
                    available_easy.append(group[0])
                    available_moderate.append(group[1])

        # Remaining groups
        while len(sectionC) < 5:
            added = False

            # Try 3 easy (12 marks)
            group = []
            for q in available_easy:
                if can_use(q, 4):
                    group.append(q)
                    if len(group) == 3:
                        break
            if len(group) == 3:
                for q in group:
                    available_easy.remove(q)
                    module_used[q.module] += 4
                sectionC.append(group)
                added = True

            # Try (1 easy + 1 moderate)
            elif len(available_easy) >= 1 and len(available_moderate) >= 1:
                for e in available_easy:
                    for m in available_moderate:
                        if can_use(e, 4) and can_use(m, 8):
                            available_easy.remove(e)
                            available_moderate.remove(m)
                            sectionC.append([e, m])
                            module_used[e.module] += 4
                            module_used[m.module] += 8
                            added = True
                            break
                    if added:
                        break

            # Try 2 moderate (6+6)
            elif len(available_moderate) >= 2:
                for i in range(len(available_moderate)):
                    for j in range(i + 1, len(available_moderate)):
                        q1 = available_moderate[i]
                        q2 = available_moderate[j]
                        if can_use(q1, 6) and can_use(q2, 6):
                            sectionC.append([q1, q2])
                            module_used[q1.module] += 6
                            module_used[q2.module] += 6
                            available_moderate.remove(q1)
                            available_moderate.remove(q2)
                            added = True
                            break
                    if added:
                        break

            # Try 1 difficult (12 mark)
            elif available_difficult:
                for q in available_difficult:
                    if can_use(q, 12):
                        sectionC.append([q])
                        module_used[q.module] += 12
                        available_difficult.remove(q)
                        added = True
                        break

            # --- RELAX MODULE MARK LIMITS ---
            if not added:
                print("⚠️ Strict limits exceeded. Relaxing module mark limits...")

                # Try 1 moderate
                if available_moderate:
                    q = available_moderate.pop()
                    sectionC.append([q])
                    module_used[q.module] += 12
                    added = True

                # Try 1 difficult
                elif available_difficult:
                    q = available_difficult.pop()
                    sectionC.append([q])
                    module_used[q.module] += 12
                    added = True

                # Try 3 easy
                elif len(available_easy) >= 3:
                    group = [available_easy.pop(), available_easy.pop(), available_easy.pop()]
                    sectionC.append(group)
                    for q in group:
                        module_used[q.module] += 4
                    added = True

                else:
                    print("❌ No more questions left to fill Section C.")
                    break



        print('\n\nLength of Section A: ', len(sectionA))
        print('\n\nLength of Section B: ', len(sectionB))
        print('\n\nLength of Section C: ', len(sectionC), '\n\n')

        print(f'\n\nModule 1 used: {module_used[1]}')
        print(f'\n\nModule 2 used: {module_used[2]}')
        print(f'\n\nModule 3 used: {module_used[3]}')
        print(f'\n\nModule 4 used: {module_used[4]}\n\n')

        # ✅ Pass data to template
        context = {
            'paper': paper,
            'date': date.today().strftime('%d-%m-%Y'),
            'sectionA': sectionA,
            'sectionB': sectionB,
            'sectionC': sectionC,
            'module_distribution': module_used,
        }
        return render(request, 'question_paper_generated.html', context)

    # GET request
    papers = ClusteredQuestion.objects.values_list('paper', flat=True).distinct()
    return render(request, 'generate_question_paper.html', {'subject_codes': papers})





def history(request):
    # Placeholder for viewing previously generated papers
    return render(request, 'history.html')

def teacher_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('teacher-dashboard')
        else:
            messages.error(request, 'Invalid credentials.')
            return redirect('teacher-login')

    return render(request, 'teacher/login.html')

@login_required
def teacher_dashboard(request):
    return render(request, 'teacher/dashboard.html')

def teacher_logout(request):
    logout(request)
    return redirect('home')


sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

@login_required
def add_question(request):
    if request.method == 'POST':
        text = request.POST.get('text')
        module = request.POST.get('module')
        difficulty = request.POST.get('difficulty')
        paper = request.POST.get('paper')

        # 📌 Optional: Get predicted cluster_label and embedding if sent from frontend
        cluster_label = int(request.POST.get('cluster_label', 0))
        embedding_json = request.POST.get('embedding')
        embedding = json.loads(embedding_json) if embedding_json else None

        # 🚫 Check if question already exists
        if ClusteredQuestion.objects.filter(text=text, module=module, paper=paper).exists():
            messages.error(request, 'Question already exists, try with another.')
            return redirect('add-question')

        # ✅ Use provided embedding if available, otherwise encode again
        if not embedding:
            embedding = sbert_model.encode([text])[0]
        else:
            # Ensure embedding is a NumPy array
            import numpy as np
            embedding = np.array(embedding)

        # ✅ Save the new question with received/predicted cluster
        question = ClusteredQuestion(
            text=text,
            module=int(module),
            difficulty=difficulty,
            paper=paper,
            cluster_label=cluster_label
        )
        question.save_embedding(embedding)
        question.save()

        messages.success(request, 'Question added successfully.')
        return redirect('add-question')

    # Render form
    papers = Question.objects.values_list('paper', flat=True).distinct()
    return render(request, 'teacher/add_question.html', {'papers': papers})

@csrf_exempt
def predict_difficulty_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('text', '').strip()
            paper = data.get('paper', '').strip()
            module = data.get('module', '').strip()  
            print(f'\ntext: {question}\n')
            print(f'\npaper: {paper}\n')
            print(f'\nmodule: {module}\n')

            if not question:
                return JsonResponse({'error': 'No question text provided'}, status=400)

            # Predict difficulty using the trained model
            try:
                difficulty_data = predict_difficulty(text=question, paper=paper, module=module)
                #print('difficulty data: ', difficulty_data)
            #difficulty = 'easy'
            except Exception as model_error:
                print("🔥 Error in prediction function:")
                print(traceback.format_exc())
                return JsonResponse({'error': 'Prediction function failed'}, status=500)    

            return JsonResponse(difficulty_data)

        except Exception as e:
            print("❌ Exception Occurred:")
            print(traceback.format_exc())  # Full traceback in console
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)