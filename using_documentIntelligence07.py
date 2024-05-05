from flask import Flask, render_template_string
import os
from openai import AzureOpenAI
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Retrieve and validate environment variables
endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
if not endpoint or not key or not openai_endpoint or not openai_api_key:
    raise ValueError("Missing required environment variables for Azure services.")

# Create Azure clients
form_recognizer_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
openai_client = AzureOpenAI(azure_endpoint=openai_endpoint, api_key=openai_api_key, api_version="2024-02-15-preview")

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF using Azure Document Analysis."""
    with open(pdf_path, "rb") as pdf_file:
        poller = form_recognizer_client.begin_analyze_document("prebuilt-document", pdf_file)
        result = poller.result()
    return [(page.page_number, ' '.join([line.content for line in page.lines])) for page in result.pages]

def compare_texts_with_azure(text1, text2):
    """Compares texts and identifies key discrepancies using Azure OpenAI."""
    messages = [
        {
            "role": "system",
            "content": "Analyze the texts from two documents and provide a structured comparison."
        },
        {
            "role": "user",
            "content": f"Please provide detailed differences between these two texts. Text from Document 1: {text1}, Text from Document 2: {text2}"
        }
    ]
    response = openai_client.chat.completions.create(model="gpt4", messages=messages, temperature=0.5, max_tokens=800)
    return response.choices[0].message.content if response.choices else "No differences detected."

@app.route("/")
def index():
    pdf_path1 = 'E:\\code\\document_compare\\40005722-Computer-Print.pdf'
    pdf_path2 = 'E:\\code\\document_compare\\40005722-Scan.pdf'
    texts1 = extract_text_from_pdf(pdf_path1)
    texts2 = extract_text_from_pdf(pdf_path2)
    pairs = zip(texts1, texts2)
    differences = [compare_texts_with_azure(text1, text2) for (_, text1), (_, text2) in pairs]

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document Text Comparison</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid black; padding: 10px; text-align: left; }
            .highlight { background-color: lightyellow; }
            ul { list-style-type: disc; padding-left: 40px; }
            li { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>Document Text Comparison</h1>
        <table>
            <tr>
                <th>Page No.</th>
                <th>Differences</th>
            </tr>
            {% for ((page1, _), (page2, _), diff) in pairs %}
            <tr>
                <td>{{ page1 }} - {{ page2 }}</td>
                <td>
                    <ul>
                        {% for line in diff.split('. ') %}
                            <li>{{ line }}</li>
                        {% endfor %}
                    </ul>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, pairs=zip(texts1, texts2, differences), zip=zip)

if __name__ == "__main__":
    app.run(debug=True)
