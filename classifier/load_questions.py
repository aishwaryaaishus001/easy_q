import pandas as pd 
import os
from classifier.models import Question

def format_paper_name(file_name):
    base = file_name.replace('.csv', '')
    code, name = base.split('_', 1)
    formatted_name = name.replace('_', ' ')
    return f'{code}: {formatted_name}'

def run():
    folder_path = 'classifier/data'
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            paper_name = format_paper_name(file_name)
            file_path = os.path.join(folder_path, file_name)
            df = pd.read_csv(file_path)

            for _, row in df.iterrows():
                # Check if the question already exists for this paper
                if not Question.objects.filter(paper=paper_name, text=row['Question']).exists():
                    Question.objects.create(
                        paper = paper_name,
                        text=row['Question'], 
                        module=row['Module']
                    )
                
            print(f'Loaded: {paper_name} ✅')

    print('Questions loaded successfully...')    