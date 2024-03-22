# Import required libraries
import os
import locale
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_community.retrievers import AzureCognitiveSearchRetriever
#from langchain import PromptTemplate
from langchain.prompts import PromptTemplate
from tenacity import retry
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

locale.getpreferredencoding = lambda: "UTF-8"

from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from flask import Flask
from azure.storage.blob import BlobServiceClient

from flask_cors import CORS

load_dotenv()  # take environment variables from .env.


AZURE_COGNITIVE_SEARCH_API_KEY = os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY")
AZURE_COGNITIVE_SEARCH_SERVICE_NAME = os.getenv("AZURE_COGNITIVE_SEARCH_SERVICE_NAME")
AZURE_COGNITIVE_SEARCH_INDEX_NAME = os.getenv("AZURE_COGNITIVE_SEARCH_INDEX_NAME")
AZURE_SERVICE_ENDPOINT = os.getenv("AZURE_SERVICE_ENDPOINT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

search_client = SearchClient(
    endpoint=AZURE_SERVICE_ENDPOINT,
    index_name="iffco_original_pre",
    credential=AzureKeyCredential(AZURE_COGNITIVE_SEARCH_API_KEY),
)


llm_name = "gpt-3.5-turbo"
index_name = "iffco_original_pre"


# Define Azure Cognitive Search as our retriever
retriever = AzureCognitiveSearchRetriever(
    service_name=AZURE_COGNITIVE_SEARCH_SERVICE_NAME,
    api_version="2023-10-01-Preview",
    api_key=AZURE_COGNITIVE_SEARCH_API_KEY,
    content_key="text",
    top_k=3,
    index_name=index_name,
)

DEFAULT_SYSTEM_PROMPT = """
You are an inquisitive and helpful assistant. Always answer as helpfully as possible while asking clarifying questions when needed. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.


You should answer to the questions briefly.



Important Note: For open-ended questions where the question has multiple possible answers and when you lack sufficient information, cross-question the user to gather more context.

If an answer is not present in the document, say I don't know; don't make an answer.

If a question does not make any sense or is not factually coherent, explain why instead of answering something that is not correct.

If you don't understand a question, ask for clarification or additional information to provide a more accurate response.

Remember, your goal is to assist and guide the user to the best of your abilities.

Understand the above details thoroughly and response accordingly keeping in mind the scale of the person if user mention the name in question.
""".strip()


def generate_prompt(prompt: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    return f"""
[INST] <>
{system_prompt}
<>

{prompt} [/INST]
""".strip()


SYSTEM_PROMPT = """
You are an inquisitive and helpful assistant.


1.For any question, if there are multiple answers, generate all the possible answers.

2.Important Note: For open-ended questions where the question has multiple possible answers and when you lack sufficient information, cross-question the user to gather more information.

3.If an answer is not present in the document, say 'I don't know'; don't make anything up or provide speculative answers and halucianate.

4.If you don't understand a question, ask for clarification or additional information to provide a more accurate response.
"""

template = generate_prompt(
    """
{context}

Question: {question}
""",
    system_prompt=SYSTEM_PROMPT,
)

prompt = PromptTemplate(template=template, input_variables=["context", "question"])


qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model_name=llm_name, temperature=0),
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={"prompt": prompt},
)


query = (
    """which all officers have authority to hire helicopter for official purposes??"""
)

result = qa_chain.invoke({"query": query})

print(result["result"])

formatted_data = ""


for doc in result["source_documents"]:
    formatted_data += f"\n{doc.metadata['source']}#page={int(doc.metadata['page'])+1}\n"

print(formatted_data)

# Blob changes
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")


blob_service_client = BlobServiceClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING
)

container_client = blob_service_client.get_container_client(
    AZURE_STORAGE_CONTAINER_NAME
)


# from question_answering import qa_chain  # Assuming you have a function for QA

app = Flask(__name__, template_folder="dist", static_folder="dist/assets")
# dist/assets #/content/sample_data
CORS(app)
# run_with_ngrok(app=app, auth_token="2ezn7hLW396NuayqxsT4Z_3qPmzfFwmRUm9yABWc2nz")  # Start ngrok when app is run


@app.route("/")
def hello():
    message = "Hello"
    return render_template("index.html")


@app.route("/api/chat", methods=["GET"])
def ReturnJSON():
    if request.method == "GET":
        query = request.args.get("query")  # Your specific query
        result = qa_chain.invoke({"query": query})

        formatted_data = ""
        for doc in result["source_documents"]:
            formatted_data += (
                f"\n{doc.metadata['source']}#page={int(doc.metadata['page']) + 1}\n"
            )

        data = {"Result": result["result"], "Source": formatted_data}
        return jsonify(data)


@app.route("/api/upload", methods=["POST"])
def FileUploadToBlob():
    try:
        if request.method == "POST":
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        blob_name = file.filename
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file)
        return jsonify({"message": "File upload successful"})
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/api/getAllBlob", methods=["GET"])
def GetAllBlob():
    try:
        if request.method == "GET":
            blob_list = list(container_client.list_blobs())
            if len(blob_list) == 0:
                return jsonify({})
            for blob in blob_list:
                print("\t" + blob.name)
            first_blob = blob_list[0]
            data = {
                "name": first_blob["name"],
                "size": first_blob["size"],
                "type": first_blob["content_settings"]["content_type"],
            }
            return jsonify(data)
    except Exception as e:
        print(e)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route("/api/deleteBlob", methods=["DELETE"])
def DeleteBlob():
    try:
        if request.method == "DELETE":
            data = request.get_json()
            file_name = data["name"]
            blob_client = container_client.get_blob_client(file_name)
            blob_client.delete_blob()
            return jsonify({"message": "File deletion successful"})
    except Exception as e:
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    app.run()
