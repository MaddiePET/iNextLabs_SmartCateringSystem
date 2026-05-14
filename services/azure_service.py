import os
import json
from datetime import datetime
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient
from models.catering_plan import CateringPlan

def create_search_client():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")
    index = os.getenv("AZURE_SEARCH_INDEX")
    if not endpoint or not key or not index: return None
    return SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))

def search_knowledge(query: str, top: int = 5) -> str:
    client = create_search_client()
    if client is None: return "Azure AI Search is not configured."
    results = client.search(search_text=query, top=top)
    docs = [json.dumps(dict(result), indent=2, default=str) for result in results]
    return "\n\n".join(docs) if docs else "No matching knowledge found."

def save_feedback(feedback_data):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string: return {"message": "Storage not configured", "blob": "none"}
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("feedback")
    try: container_client.create_container()
    except: pass
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_id = feedback_data.get("customer_feedback", {}).get("plan_id", timestamp)
    blob_name = f"feedback_{plan_id}.json"
    container_client.upload_blob(name=blob_name, data=json.dumps(feedback_data, indent=2), overwrite=True)
    return {"message": "Feedback saved", "blob": blob_name}

def save_plan_to_blob(plan: CateringPlan) -> str:
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string: return "Not Configured"
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client(os.getenv("AZURE_STORAGE_CONTAINER", "plans"))
    try: container_client.create_container()
    except: pass
    blob_name = f"{plan.plan_id}.json"
    container_client.upload_blob(name=blob_name, data=json.dumps(plan.model_dump(), indent=2), overwrite=True)
    return blob_name
