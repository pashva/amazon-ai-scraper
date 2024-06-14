import ollama
import html2text
import json

def generate_json(html_content):
    h = html2text.HTML2Text()
    h.ignore_links = True
    html2text_content = h.handle(html_content)
    response = ollama.generate(model="mistral", prompt=f"""
    {html2text_content}
    Generate a strucured output json in the below format for the above content:
        "order_id" : "",
        "order_date" : "",
        "shipping_to" : ("name": "", "address": ""),
        "products_ordered" : ("name" : "", "quantity" : "", "price" : ""),
    """, format="json",stream=False)
    try:
        answer = json.loads(response['response'])
    except:
        answer = json.loads('{"error": "Could not generate JSON from the given content"}')
    return answer
    