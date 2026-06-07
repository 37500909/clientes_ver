import sys
from apify_client import ApifyClient

# Load .env file manually if it exists
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    os.environ[parts[0].strip()] = parts[1].strip()

token = os.environ.get("APIFY_API_TOKEN")
if not token:
    print("Error: APIFY_API_TOKEN env variable is not set.")
    sys.exit(1)

client = ApifyClient(token)

print("Starting test run...")
run_input = {
    "searchStringsArray": ["agencia de marketing"],
    "locationQuery": "San Miguel de Tucumán, Tucumán, Argentina",
    "maxCrawledPlacesPerSearch": 3,
    "language": "es"
}

try:
    print("Calling compass/crawler-google-places actor...")
    run_info = client.actor("compass/crawler-google-places").call(run_input=run_input)
    print(f"Run object type: {type(run_info)}")
    print(f"Run object attributes: {dir(run_info)}")
    
    # Try dictionary-like get or attribute-like access
    dataset_id = None
    if isinstance(run_info, dict):
        dataset_id = run_info.get("defaultDatasetId")
    elif hasattr(run_info, "default_dataset_id"):
        dataset_id = run_info.default_dataset_id
    elif hasattr(run_info, "defaultDatasetId"):
        dataset_id = run_info.defaultDatasetId
    else:
        # Check by printing dictionary
        print(f"Run object as dict: {run_info.__dict__ if hasattr(run_info, '__dict__') else str(run_info)}")
        
    print(f"Dataset ID determined: {dataset_id}")
    
    if dataset_id:
        count = 0
        for item in client.dataset(dataset_id).iterate_items():
            print(f"\nItem {count+1}:")
            print(f"Title: {item.get('title')}")
            print(f"Address: {item.get('address')}")
            print(f"Phone: {item.get('phone')}")
            print(f"Website: {item.get('website')}")
            print("Keys present in item:")
            print(sorted(list(item.keys())))
            
            # Look for social media keys
            social_keys = [k for k in item.keys() if any(s in k.lower() for s in ['facebook', 'instagram', 'linkedin', 'twitter', 'social', 'contact'])]
            if social_keys:
                print("Social/Contact keys found:")
                for sk in social_keys:
                    print(f"  {sk}: {item[sk]}")
            else:
                print("No social/contact keys found directly in item.")
                
            count += 1
except Exception as e:
    print(f"Error occurred during test run: {e}")
