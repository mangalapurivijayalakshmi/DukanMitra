import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "బియ్యం స్టాక్ తక్కువగా ఉంటే ఏం చేయాలి? తెలుగులో చెప్పు."}]}],
)

print(response["output"]["message"]["content"][0]["text"])