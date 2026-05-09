import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_KEY")
index_name = os.getenv("AZURE_SEARCH_INDEX", "catering-knowledge")

credential = AzureKeyCredential(key)

index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="title", type=SearchFieldDataType.String),
    SearchableField(name="category", type=SearchFieldDataType.String),
    SearchableField(name="content", type=SearchFieldDataType.String),
]

index = SearchIndex(name=index_name, fields=fields)

try:
    index_client.delete_index(index_name)
except Exception:
    pass

index_client.create_index(index)

files = [
    ("supplier_data", "Supplier Data", "supplier", "knowledge/supplier_data.txt"),
    ("menu_catalog", "Menu Catalog", "menu", "knowledge/menu_catalog.txt"),
    ("inventory_rules", "Inventory Rules", "inventory", "knowledge/inventory_rules.txt"),
    ("compliance_standards", "Compliance Standards", "compliance", "knowledge/compliance_standards.txt"),
    ("logistics_rules", "Logistics Rules", "logistics", "knowledge/logistics_rules.txt"),
    ("risk_rulebook", "Risk Rulebook", "risk", "knowledge/risk_rulebook.txt"),
    ("feedback_criteria", "Feedback Criteria", "feedback", "knowledge/feedback_criteria.txt"),
]

documents = []

for doc_id, title, category, path in files:
    with open(path, "r", encoding="utf-8") as f:
        documents.append({
            "id": doc_id,
            "title": title,
            "category": category,
            "content": f.read(),
        })

search_client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=credential,
)

search_client.upload_documents(documents)

print(f"Uploaded {len(documents)} documents to Azure AI Search index: {index_name}")