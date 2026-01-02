# Ocr

Title: /ocr | liteLLM

URL Source: https://docs.litellm.ai/docs/ocr

Published Time: Fri, 02 Jan 2026 04:28:16 GMT

Markdown Content:
| Feature | Supported |
| --- | --- |
| Cost Tracking | ✅ |
| Logging | ✅ (Basic Logging not supported) |
| Load Balancing | ✅ |
| Supported Providers | `mistral`, `azure_ai`, `vertex_ai` |

tip

**LiteLLM Python SDK Usage**[​](https://docs.litellm.ai/docs/ocr#litellm-python-sdk-usage "Direct link to litellm-python-sdk-usage")
------------------------------------------------------------------------------------------------------------------------------------

### Quick Start[​](https://docs.litellm.ai/docs/ocr#quick-start "Direct link to Quick Start")

`from litellm import ocrimport osos.environ["MISTRAL_API_KEY"] = "sk-.."response = ocr(    model="mistral/mistral-ocr-latest",    document={        "type": "document_url",        "document_url": "https://arxiv.org/pdf/2201.04234"    })# Access extracted textfor page in response.pages:    print(f"Page {page.index}:")    print(page.markdown)`

### Async Usage[​](https://docs.litellm.ai/docs/ocr#async-usage "Direct link to Async Usage")

`from litellm import aocrimport os, asyncioos.environ["MISTRAL_API_KEY"] = "sk-.."async def test_async_ocr():     response = await aocr(        model="mistral/mistral-ocr-latest",        document={            "type": "document_url",            "document_url": "https://arxiv.org/pdf/2201.04234"        }    )        # Access extracted text    for page in response.pages:        print(f"Page {page.index}:")        print(page.markdown)asyncio.run(test_async_ocr())`

### Using Base64 Encoded Documents[​](https://docs.litellm.ai/docs/ocr#using-base64-encoded-documents "Direct link to Using Base64 Encoded Documents")

`import base64from litellm import ocr# Encode PDF to base64with open("document.pdf", "rb") as f:    base64_pdf = base64.b64encode(f.read()).decode('utf-8')response = ocr(    model="mistral/mistral-ocr-latest",    document={        "type": "document_url",        "document_url": f"data:application/pdf;base64,{base64_pdf}"    })`

### Optional Parameters[​](https://docs.litellm.ai/docs/ocr#optional-parameters "Direct link to Optional Parameters")

`response = ocr(    model="mistral/mistral-ocr-latest",    document={        "type": "document_url",        "document_url": "https://example.com/doc.pdf"    },    # Optional Mistral parameters    pages=[0, 1, 2],              # Only process specific pages    include_image_base64=True,     # Include extracted images    image_limit=10,                # Max images to return    image_min_size=100             # Min image size to include)`

**LiteLLM Proxy Usage**[​](https://docs.litellm.ai/docs/ocr#litellm-proxy-usage "Direct link to litellm-proxy-usage")
---------------------------------------------------------------------------------------------------------------------

LiteLLM provides a Mistral API compatible `/ocr` endpoint for OCR calls.

**Setup**

Add this to your litellm proxy config.yaml

`model_list:  - model_name: mistral-ocr    litellm_params:      model: mistral/mistral-ocr-latest      api_key: os.environ/MISTRAL_API_KEY`

Start litellm

`litellm --config /path/to/config.yaml# RUNNING on http://0.0.0.0:4000`

Test request

`curl http://0.0.0.0:4000/v1/ocr \  -H "Authorization: Bearer sk-1234" \  -H "Content-Type: application/json" \  -d '{    "model": "mistral-ocr",    "document": {        "type": "document_url",        "document_url": "https://arxiv.org/pdf/2201.04234"    }  }'`

**Request/Response Format**[​](https://docs.litellm.ai/docs/ocr#requestresponse-format "Direct link to requestresponse-format")
-------------------------------------------------------------------------------------------------------------------------------

### Example Request[​](https://docs.litellm.ai/docs/ocr#example-request "Direct link to Example Request")

`{    "model": "mistral/mistral-ocr-latest",    "document": {        "type": "document_url",        "document_url": "https://arxiv.org/pdf/2201.04234"    },    "pages": [0, 1, 2],              # Optional: specific pages to process    "include_image_base64": True,     # Optional: include extracted images    "image_limit": 10,                # Optional: max images to return    "image_min_size": 100             # Optional: min image size in pixels}`

### Request Parameters[​](https://docs.litellm.ai/docs/ocr#request-parameters "Direct link to Request Parameters")

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `model` | string | Yes | The OCR model to use (e.g., `"mistral/mistral-ocr-latest"`) |
| `document` | object | Yes | Document to process. Must contain `type` and URL field |
| `document.type` | string | Yes | Either `"document_url"` for PDFs/docs or `"image_url"` for images |
| `document.document_url` | string | Conditional | URL to the document (required if `type` is `"document_url"`) |
| `document.image_url` | string | Conditional | URL to the image (required if `type` is `"image_url"`) |
| `pages` | array | No | List of specific page indices to process (0-indexed) |
| `include_image_base64` | boolean | No | Whether to include extracted images as base64 strings |
| `image_limit` | integer | No | Maximum number of images to return |
| `image_min_size` | integer | No | Minimum size (in pixels) for images to include |

#### Document Format Examples[​](https://docs.litellm.ai/docs/ocr#document-format-examples "Direct link to Document Format Examples")

**For PDFs and documents:**

`{  "type": "document_url",  "document_url": "https://example.com/document.pdf"}`

**For images:**

`{  "type": "image_url",  "image_url": "https://example.com/image.png"}`

**For base64-encoded content:**

`{  "type": "document_url",  "document_url": "data:application/pdf;base64,JVBERi0xLjQKJ..."}`

### Response Format[​](https://docs.litellm.ai/docs/ocr#response-format "Direct link to Response Format")

The response follows Mistral's OCR format with the following structure:

`{  "pages": [    {      "index": 0,      "markdown": "# Document Title\n\nExtracted text content...",      "dimensions": {        "dpi": 200,        "height": 2200,        "width": 1700      },      "images": [        {          "image_base64": "base64string...",          "bbox": {            "x": 100,            "y": 200,            "width": 300,            "height": 400          }        }      ]    }  ],  "model": "mistral-ocr-2505-completion",  "usage_info": {    "pages_processed": 29,    "doc_size_bytes": 3002783  },  "document_annotation": null,  "object": "ocr"}`

#### Response Fields[​](https://docs.litellm.ai/docs/ocr#response-fields "Direct link to Response Fields")

| Field | Type | Description |
| --- | --- | --- |
| `pages` | array | List of processed pages with extracted content |
| `pages[].index` | integer | Page number (0-indexed) |
| `pages[].markdown` | string | Extracted text in Markdown format |
| `pages[].dimensions` | object | Page dimensions (dpi, height, width in pixels) |
| `pages[].images` | array | Extracted images from the page (if `include_image_base64=true`) |
| `model` | string | The model used for OCR processing |
| `usage_info` | object | Processing statistics (pages processed, document size) |
| `document_annotation` | object | Optional document-level annotations |
| `object` | string | Always `"ocr"` for OCR responses |

**Supported Providers**[​](https://docs.litellm.ai/docs/ocr#supported-providers "Direct link to supported-providers")
---------------------------------------------------------------------------------------------------------------------

| Provider | Link to Usage |
| --- | --- |
| Mistral AI | [Usage](https://docs.litellm.ai/docs/ocr#quick-start) |
| Azure AI | [Usage](https://docs.litellm.ai/docs/providers/azure_ocr) |
| Vertex AI | [Usage](https://docs.litellm.ai/docs/providers/vertex_ocr) |
