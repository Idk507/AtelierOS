# Azure OpenAI adapters

The studio uses a deterministic fixture for concept previews. Azure REST adapters support chat, vision, image generation and embeddings. The smoke command exercises those adapters separately with synthetic inputs. No live deployment has been verified.

## Configuration

Set `ATELIER_AZURE_ENABLED=true` in the smoke process and configure `ATELIER_AZURE_ENDPOINT` as an HTTPS `*.openai.azure.com` resource root. Supply one credential using `ATELIER_AZURE_API_KEY` or a short-lived `ATELIER_AZURE_ENTRA_TOKEN`. The process does not load `.env` automatically. Configure the corresponding `ATELIER_AZURE_CHAT_DEPLOYMENT`, `ATELIER_AZURE_VISION_DEPLOYMENT`, `ATELIER_AZURE_IMAGE_DEPLOYMENT` or `ATELIER_AZURE_EMBEDDING_DEPLOYMENT` explicitly. A missing deployment returns `azure_capability_disabled`.

```powershell
uv run --frozen python -m scripts.azure_smoke image
uv run --frozen python -m scripts.azure_smoke chat --live --allow-charges
uv run --frozen python -m scripts.azure_smoke vision --live --allow-charges
uv run --frozen python -m scripts.azure_smoke image --live --allow-charges --allow-image-generation
```

Check the deployment pricing and quota before running a live probe. The command sends one request, caps chat output at 256 tokens and requests one low-quality image. It reports the deployment, duration, request ID and token usage when the provider supplies them. Live cost is unknown. The command emits metadata only and retains no image files. It reports 429, timeouts, filtering and malformed output separately. Retries require a fresh operator decision, especially if a timeout leaves the provider outcome unknown.

Chat and vision use the Azure v1 chat completions endpoint. Vision takes one normalized JPEG and sends it inline. Image generation uses the v1 preview endpoint, requests JPEG output and retains a normalized thumbnail. Image editing remains open. [Azure vision documentation](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/gpt-with-vision) · [Azure image generation documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/dall-e)
