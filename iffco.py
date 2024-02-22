# Import required libraries
import os
import json
import openai
from openai import AzureOpenAI
#new imports
from langchain_openai import ChatOpenAI
from langchain_community.retrievers import AzureCognitiveSearchRetriever
from langchain_community.document_loaders import PyPDFLoader
#from dotenv import load_dotenv
from tenacity import retry, wait_random_exponential, stop_after_attempt
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient, SearchIndexingBufferedSender
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryCaptionResult,
    QueryAnswerResult,
    SemanticErrorMode,
    SemanticErrorReason,
    SemanticSearchResultsType,
    QueryType,
    VectorizedQuery,
    VectorQuery,
    VectorFilterMode,
)
from azure.search.documents.indexes.models import (
    ExhaustiveKnnAlgorithmConfiguration,
    ExhaustiveKnnParameters,
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SearchIndex,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SearchField,
    SemanticSearch,
    VectorSearch,
    HnswAlgorithmConfiguration,
    HnswParameters,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchProfile,
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    ExhaustiveKnnParameters,
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SearchField,
    VectorSearch,
    HnswParameters,
    VectorSearch,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)
#from langchain.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.embeddings.openai import OpenAIEmbeddings
#from langchain.chat_models import ChatOpenAI
#from langchain.retrievers import AzureCognitiveSearchRetriever
import locale
locale.getpreferredencoding = lambda: "UTF-8"
from flask import Flask, render_template, jsonify, request
from flask_ngrok2 import run_with_ngrok


search_client = SearchClient(endpoint='https://testaicognitivesearch1.search.windows.net', index_name="iffco_original_pre",\
                             credential= AzureKeyCredential('6BogobGfe1c6vr67EzV6BgVB2HuIDhwcAboNznRQNlAzSeBE9FFi'))



llm_name ="gpt-3.5-turbo"
index_name = 'iffco_original_pre'

os.environ["AZURE_COGNITIVE_SEARCH_SERVICE_NAME"] = "testaicognitivesearch1"
os.environ["AZURE_COGNITIVE_SEARCH_INDEX_NAME"] = index_name
os.environ["AZURE_COGNITIVE_SEARCH_API_KEY"] = "6BogobGfe1c6vr67EzV6BgVB2HuIDhwcAboNznRQNlAzSeBE9FFi"
os.environ["OPENAI_API_KEY"] = "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" #"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"



# Define Azure Cognitive Search as our retriever
retriever = AzureCognitiveSearchRetriever(service_name='testaicognitivesearch1',\
                                          api_version='2023-10-01-Preview',\
                                          api_key='6BogobGfe1c6vr67EzV6BgVB2HuIDhwcAboNznRQNlAzSeBE9FFi',\
                                          content_key="text", top_k=3, index_name=index_name)


qa_chain = RetrievalQA.from_chain_type(llm=ChatOpenAI(model_name=llm_name, temperature=0),\
                                 chain_type="stuff", retriever=retriever, \
                                 return_source_documents=True)



query = """which all officers have authority to hire helicopter for official purposes??"""

result = qa_chain.invoke({"query": query}) #qa_chain

print(result['result'])

formatted_data = ""

 
for doc in result['source_documents']:
    formatted_data += f"\n{doc.metadata['source']}#page={int(doc.metadata['page'])+1}\n"

print(formatted_data)




# from question_answering import qa_chain  # Assuming you have a function for QA

app = Flask(__name__, template_folder="build", static_folder="build/static") #/content/sample_data
run_with_ngrok(app=app, auth_token="2ezn7hLW396NuayqxsT4Z_3qPmzfFwmRUm9yABWc2nz")  # Start ngrok when app is run

@app.route("/")
def hello():
    message = "Hello"
    return render_template('index.html')

@app.route('/api/chat', methods=['GET'])
def ReturnJSON():
    if request.method == 'GET':
        query = request.args.get('query')  # Your specific query
        result = qa_chain.invoke({"query": query}) #qa_chain

        formatted_data = ""
        for doc in result['source_documents']:
            formatted_data += f"\n{doc.metadata['source']}#page={int(doc.metadata['page']) + 1}\n"

        data = {
            "Result": result['result'],
            "Source": formatted_data
        }
        return jsonify(data)

if __name__ == '__main__':
    app.run()
