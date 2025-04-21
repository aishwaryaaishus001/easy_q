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
import random



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
        original_distribution = {
            1: int(request.POST.get('module1')),
            2: int(request.POST.get('module2')),
            3: int(request.POST.get('module3')),
            4: int(request.POST.get('module4')),
        }
        total = sum(original_distribution.values())
        if total != 124:
            messages.error(request, "❌ The total module-wise mark distribution must be exactly 124.")
            return redirect('generate_question_paper') 
        
        print('Original limits: ', original_distribution)
        
        # Check if the entered values can be constructed using 4,6,8,12
        if is_distribution_possible(original_distribution):
            module_limits = original_distribution
            print("\n✅ Original distribution is valid with 4/6/8/12\n")
        else:
            module_limits = get_optimal_distribution(original_distribution)
            messages.warning(
                request,
                f"⚠️ The entered distribution is not possible using 4,6,8,12 mark patterns. "
                f"Switched to optimal nearby distribution: {module_limits}"
            )
            print(f"\n⚠️ Adjusted to optimal: {module_limits}\n")

        module_used = defaultdict(int)
        print('\n\nModule limits: ', module_limits, '\n\n')
        module_pattern_used = defaultdict(list)  # Track the exact marks used per module


        def can_use(q, marks):
            mod = q.module
            print(f'{module_used[mod]} + {marks} <= {module_limits[mod]}')
            print(f'returned: {module_used[mod] + marks <= module_limits[mod]}\n\n')
            return module_used[mod] + marks <= module_limits[mod]
        
        def can_use_group(group, marks_list):
            """Check if a group of questions (with matching marks list) can be added."""
            temp_usage = defaultdict(int)
            for q, m in zip(group, marks_list):
                temp_usage[q.module] += m
            return all(module_used[mod] + temp_usage[mod] <= module_limits[mod] for mod in temp_usage)
        
        def is_partial_match(partial, full):
            """Check if all elements in `partial` can be found in `full` with correct frequency."""
            #from collections import Counter
            partial_counts = Counter(partial)
            full_counts = Counter(full)
            for mark in partial_counts:
                if partial_counts[mark] > full_counts.get(mark, 0):
                    return False
            return True
        
        def can_use_with_pattern_check(q, marks):
            mod = q.module
            # Simulate new pattern
            new_pattern = module_pattern_used[mod] + [marks]
            new_sum = module_used[mod] + marks

            if new_sum > module_limits[mod]:
                return False

            valid_combos = get_valid_combinations(module_limits[mod])
            print(f'module: {mod} *** new pattern: {new_pattern} *** valid combos: {valid_combos}\n\n')

            # Check if the simulated new pattern is still valid (subset of any combo)
            for combo in valid_combos:
                #print(f'\n for module: {mod} *** new pattern: {new_pattern} *** combo: {combo}\n')
                if is_partial_match(new_pattern, combo):
                    print('returned true\n')
                    return True  # Don’t add here, just return True
            print('returned false\n')
            return False


        # Get all questions for the paper
        questions = ClusteredQuestion.objects.filter(paper=paper)

        easy_qs = list(questions.filter(difficulty="easy"))
        moderate_qs = list(questions.filter(difficulty="medium"))
        difficult_qs = list(questions.filter(difficulty="hard"))

        # Shuffle for randomness
        random.shuffle(easy_qs)
        random.shuffle(moderate_qs)
        random.shuffle(difficult_qs)

        # ---------------- Section A: 6 questions × 4 marks ----------------
        sectionA = []
        print('\n\nSection A: ')
        for q in easy_qs + moderate_qs:
            if len(sectionA) < 6 and can_use_with_pattern_check(q, 4):
                print(f'{q} added, module: {q.module}\n')
                sectionA.append(q)
                module_used[q.module] += 4
                module_pattern_used[q.module].append(4)


        # ---------------- Section B: 5 questions × 8 marks ----------------
        sectionB = []
        print('\n\nSection B: ')
        for q in difficult_qs + moderate_qs:
            if len(sectionB) < 5 and can_use_with_pattern_check(q, 8):
                print(f'{q} added, module: {q.module}\n')
                sectionB.append(q)
                module_used[q.module] += 8
                module_pattern_used[q.module].append(8)


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
            if can_use_with_pattern_check(group[0], 4) and can_use_with_pattern_check(group[1], 4) and can_use_with_pattern_check(group[2], 4):
                sectionC.append(group)
                for q in group:
                    module_used[q.module] += 4
                    module_pattern_used[q.module].append(4)

            else:
                # Return them back if not usable
                available_easy.extend(group)

        # 2 groups of (1 easy + 1 moderate)
        for _ in range(2):
            if len(available_easy) >= 1 and len(available_moderate) >= 1:
                group = [available_easy.pop(), available_moderate.pop()]
                if can_use_with_pattern_check(group[0], 4) and can_use_with_pattern_check(group[1], 8):
                    sectionC.append(group)
                    module_used[group[0].module] += 4
                    module_pattern_used[group[0].module].append(4)

                    module_used[group[1].module] += 8
                    module_pattern_used[group[1].module].append(8)

                else:
                    available_easy.append(group[0])
                    available_moderate.append(group[1])

        # Remaining groups
        while len(sectionC) < 5:
            added = False

            # Try 3 easy (12 marks)
            group = []
            for q in available_easy:
                if module_limits[q.module] - module_used[q.module] != 6:
                    if can_use_with_pattern_check(q, 4):
                        group.append(q)
                        if len(group) == 3:
                            break
            if len(group) == 3:
                if can_use_with_pattern_check(group[0], 4) and can_use_with_pattern_check(group[1], 4) and can_use_with_pattern_check(group[2], 4):
                    print('\nHERe\n')
                    for q in group:
                        available_easy.remove(q)
                        module_used[q.module] += 4
                        module_pattern_used[q.module].append(4)

                    sectionC.append(group)
                    print(f'{group} added in section c\n')
                    added = True
                else:
                    available_easy.extend(group)    

            # Try (1 easy + 1 moderate)
            elif len(available_easy) >= 1 and len(available_moderate) >= 1:
                group = []
                for e in available_easy:
                    for m in available_moderate:
                        if module_limits[e.module] - module_used[e.module] != 6 or module_limits[m.module] - module_used[m.module] != 6:
                            if can_use_with_pattern_check(e, 4) and can_use_with_pattern_check(m, 8):
                                available_easy.remove(e)
                                available_moderate.remove(m)
                                group.extend([e, m])
                                if can_use_with_pattern_check(group[0], 4) and can_use_with_pattern_check(group[1], 8):
                                    sectionC.append(group)
                                    print(f'{group} added in section c\n')

                                    module_used[group[0].module] += 4
                                    module_pattern_used[group[0].module].append(4)

                                    module_used[group[1].module] += 8
                                    module_pattern_used[group[1].module].append(8)

                                    added = True
                                    break
                                else:
                                    available_easy.append(group[0])
                                    available_moderate.append(group[1])
                    if added:
                        break

            # Try 2 moderate (6+6)
            elif len(available_moderate) >= 2:
                group = []
                for i in range(len(available_moderate)):
                    for j in range(i + 1, len(available_moderate)):
                        q1 = available_moderate[i]
                        q2 = available_moderate[j]
                        if module_limits[q1.module]-module_used[q1.module] != 4 or module_limits[q1.module]-module_used[q1.module] != 4:
                            if can_use_with_pattern_check(q1, 6) and can_use_with_pattern_check(q2, 6):
                                available_moderate.remove(q1)
                                available_moderate.remove(q2)
                                group.append([q1, q2])
                                if can_use_with_pattern_check(group[0], 6) and can_use_with_pattern_check(group[1], 6):
                                    sectionC.append(group)
                                    print(f'{group} added in section c\n')

                                    module_used[group[0].module] += 6
                                    module_pattern_used[group[0].module].append(6)

                                    module_used[group[1].module] += 6
                                    module_pattern_used[group[1].module].append(6)

                                    added = True
                                    break
                                else:
                                    available_moderate.extend(group)
                    if added:
                        break

            # Try 1 difficult (12 mark)
            elif available_difficult:
                for q in available_difficult:
                    if module_limits[q.module]-module_used[q.module] >= 12:
                        if can_use_with_pattern_check(q, 12):
                            sectionC.append([q])
                            print(f'{q} added in section c\n')
                            module_used[q.module] += 12
                            module_pattern_used[q.module].append(12)

                            available_difficult.remove(q)
                            added = True
                            break

            # --- RELAX MODULE MARK LIMITS ---
            if not added:
                print(f'length on section c: {len(sectionC)}\n')
                print("⚠️ Strict limits exceeded. Relaxing module mark limits...")

                # Try 1 moderate
                if available_moderate:
                    q = available_moderate.pop()
                    sectionC.append([q])
                    module_used[q.module] += 12
                    module_pattern_used[q.module].append(12)

                    added = True

                # Try 1 difficult
                elif available_difficult:
                    q = available_difficult.pop()
                    sectionC.append([q])
                    module_used[q.module] += 12
                    module_pattern_used[q.module].append(12)

                    added = True

                # Try 3 easy
                elif len(available_easy) >= 3:
                    group = [available_easy.pop(), available_easy.pop(), available_easy.pop()]
                    sectionC.append(group)
                    for q in group:
                        module_used[q.module] += 4
                        module_pattern_used[q.module].append(4)

                    added = True

                else:
                    print("❌ No more questions left to fill Section C.")
                    break



        print('\n\nLength of Section A: ', len(sectionA))
        print('\n\nLength of Section B: ', len(sectionB))
        print('\n\nLength of Section C: ', len(sectionC), '\n\n')
        print("\n📊 Final module usage summary:")

        '''for module_id, marks_used in module_used.items():
            limit = module_limits[module_id]
            print(f"Module {module_id} used: {marks_used} / {limit}")
            if marks_used > limit:
                print(f"❌ Module {module_id} exceeded limit. Discarding this paper and retrying...\n")
                return None  # or trigger regeneration logic'''


        for mod in module_limits:
            #pattern = sorted(module_pattern_used[mod])
            #valid_patterns = [sorted(p) for p in get_valid_combinations(module_limits[mod])]
            #print(f'patterns for {mod}: {valid_patterns}')
            
            #if pattern in valid_patterns:
                #print(f"✅ Module {mod} pattern {pattern} is valid for limit {module_limits[mod]}")
            #else:
                #print(f"❌ Module {mod} pattern {pattern} is INVALID for limit {module_limits[mod]}")
            print(f'module: {mod} *** limit: {module_limits[mod]} *** final pattern: {module_pattern_used[mod]} *** used: {module_used}\n\n')


        # ✅ Pass data to template
        context = {
            'paper': paper,
            'sectionA': sectionA,
            'sectionB': sectionB,
            'sectionC': sectionC,
            'module_distribution': module_used,
        }

        print(f'\n\nModule used of 1: {module_used[1]}\n')
        print(f'Module used of 2: {module_used[2]}\n')
        print(f'Module used of 3: {module_used[3]}\n')
        print(f'Module used of 4: {module_used[4]}\n\n')
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