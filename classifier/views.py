from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from . models import Question, ClusteredQuestion
import random


# Create your views here.
def home(request):
    return render(request, 'home.html')

def generate_question_paper(request):
    if request.method == 'POST':
        paper = request.POST.get('paper')
        print('paper: ', paper)

        # Filter questions by subject
        questions = ClusteredQuestion.objects.filter(paper=paper)
        print('questions: ', questions)

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
        print('\n\n\nAvailable easy: ', available_easy, '\n\n\n')
        print('\n\n\nAvailable moderate: ', available_moderate, '\n\n\n')

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
        print("section C:", sectionC)




        print('section A: ', sectionA)
        print('section B: ', sectionB)
        print('section C: ', sectionC)


        context = {
            'paper': paper,
            'sectionA': sectionA,
            'sectionB': sectionB,
            'sectionC': sectionC,
        }
        return render(request, 'question_paper_generated.html', context)

    # Render form page on GET
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