import requests
import json
from requests.auth import HTTPBasicAuth


def get_index_mapping(input_host, input_index):
    url = f"{input_host}/{input_index}/_mapping"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to get mapping: {response.text}")
        return None
    return response.json()


def create_index(output_host, output_index, mapping):
    url = f"{output_host}/{output_index}"
    settings = {
        "settings": {"index.mapping.total_fields.limit": 2000},
        "mappings": {"properties": mapping},
    }
    headers = {"Content-Type": "application/json"}
    response = requests.put(url, headers=headers, data=json.dumps(settings))
    if response.status_code != 200:
        print(f"Failed to create index: {response.text}")
        return False
    return True


def scroll_and_index_documents(input_host, input_index, output_host, output_index):
    # Initialize the scroll request
    url = f"{input_host}/{input_index}/_search?scroll=1m"
    query = {"query": {"match_all": {}}, "size": 1000}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(query))
    if response.status_code != 200:
        print(f"Failed to initiate scroll: {response.text}")
        return

    result = response.json()
    scroll_id = result.get("_scroll_id")
    if not scroll_id:
        print("Failed to obtain scroll ID")
        return

    while True:
        # Fetch documents using scroll ID
        url = f"{input_host}/_search/scroll"
        scroll_query = {"scroll": "1m", "scroll_id": scroll_id}
        response = requests.post(url, headers=headers, data=json.dumps(scroll_query))
        if response.status_code != 200:
            print(f"Failed to continue scroll: {response.text}")
            break

        result = response.json()
        hits = result.get("hits", {}).get("hits", [])
        if not hits:
            break

        # Index documents to the destination index
        for hit in hits:
            doc_id = hit["_id"]
            source = hit["_source"]
            index_url = f"{output_host}/{output_index}/_doc/{doc_id}"
            response = requests.post(
                index_url, headers=headers, data=json.dumps(source)
            )
            if response.status_code != 201:
                print(f"Failed to index document ID {doc_id}: {response.text}")

        scroll_id = result.get("_scroll_id")
        if not scroll_id:
            break


def main():
    input_host = "http://pjeelk68.trf1.gov.br:9200"
    input_index = "pje2g_documento"
    output_host = "http://172.16.6.33:9220"
    output_index = "pje2g_documento_v8"

    mapping = get_index_mapping(input_host, input_index)
    if not mapping:
        return

    properties = mapping[input_index]["mappings"]["documento"]["properties"]
    if not create_index(output_host, output_index, properties):
        return

    scroll_and_index_documents(input_host, input_index, output_host, output_index)


if __name__ == "__main__":
    main()
