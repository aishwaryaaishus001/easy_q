from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from . models import Question, ClusteredQuestion
from collections import defaultdict
import random



# Create your views here.
def home(request):
    return render(request, 'home.html')

'''def generate_question_paper(request):
    if request.method == 'POST':
        paper = request.POST.get('paper')
        module1_marks = int(request.POST.get('module1'))
        module2_marks = int(request.POST.get('module2'))
        module3_marks = int(request.POST.get('module3'))
        module4_marks = int(request.POST.get('module4'))

        print('paper: ', paper)
        print('Module 1: ', module1_marks)
        print('Module 2: ', module2_marks)
        print('Module 3: ', module3_marks)
        print('Module 4: ', module4_marks)

        # Filter questions by subject
        questions = ClusteredQuestion.objects.filter(paper=paper)
        #print('questions: ', questions)

        easy_qs = list(questions.filter(difficulty="easy"))
        moderate_qs = list(questions.filter(difficulty="medium"))
        difficult_qs = list(questions.filter(difficulty="difficult"))

        sectionA_pool = easy_qs + moderate_qs
        sectionB_pool = difficult_qs or moderate_qs + difficult_qs or easy_qs
        #sectionC_pool = [q for q in (easy_qs + moderate_qs) if q not in sectionA_pool]

        # Shuffle for randomness
        random.shuffle(sectionA_pool)
        random.shuffle(sectionB_pool)
        #random.shuffle(sectionC_pool)

        sectionA = sectionA_pool[:6]
        sectionB = sectionB_pool[:5]

        # Ensure uniqueness from sectionA
        available_easy = [q for q in easy_qs if q not in sectionA]
        available_moderate = [q for q in moderate_qs if q not in sectionA and q not in sectionB]

        random.shuffle(available_easy)
        random.shuffle(available_moderate)
        #print('\n\n\nAvailable easy: ', available_easy, '\n\n\n')
        #print('\n\n\nAvailable moderate: ', available_moderate, '\n\n\n')

        sectionC = []

        # 1 question with 3 easy subquestions
        if len(available_easy) >= 3:
            three_easy = [available_easy.pop(), available_easy.pop(), available_easy.pop()]
            sectionC.append(three_easy)
        else:
            print("❌ Not enough easy questions for 3-subquestion block in Section C")

        # 2 questions with 1 easy + 1 moderate
        for _ in range(2):
            if len(available_easy) >= 1 and len(available_moderate) >= 1:
                mixed = [available_easy.pop(), available_moderate.pop()]
                sectionC.append(mixed)
            else:
                print("❌ Not enough easy or moderate questions for 2-subquestion block in Section C")

        # 2 standalone moderate questions
        for _ in range(2):
            if len(available_moderate) >= 1:
                sectionC.append([available_moderate.pop()])
            else:
                print("❌ Not enough moderate questions for single-question blocks in Section C")


        # print to verify structure
        #print("section C:", sectionC)




        #print('section A: ', sectionA)
        #print('section B: ', sectionB)
        #print('section C: ', sectionC)


        context = {
            'paper': paper,
            'sectionA': sectionA,
            'sectionB': sectionB,
            'sectionC': sectionC,
        }
        return render(request, 'question_paper_generated.html', context)

    # Render form page on GET
    papers = ClusteredQuestion.objects.values_list('paper', flat=True).distinct()
    return render(request, 'generate_question_paper.html', {'subject_codes': papers})'''

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

        # ✅ Pass data to template
        context = {
            'paper': paper,
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

@login_required
def add_question(request):
    if request.method == 'POST':
        text = request.POST.get('text')
        module = request.POST.get('module')
        mark = request.POST.get('mark')
        difficulty = request.POST.get('difficulty')

        Question.objects.create(
            text=text,
            module=module,
            mark=mark,
            difficulty=difficulty
        )

        messages.success(request, 'Question added successfully.')
        return HttpResponseRedirect(reverse('add-question'))

    return render(request, 'teacher/add_question.html')