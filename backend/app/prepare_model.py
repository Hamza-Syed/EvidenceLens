"""Download/cache the configured model before serving uploads."""
from .config import Settings
from .embeddings import FastEmbedProvider


def main() -> None:
    settings = Settings.from_env()
    vector = FastEmbedProvider(settings).embed_query("Prepare local semantic retrieval.")
    print(f"Ready: {settings.embedding_model}, {len(vector)} dimensions, cache: {settings.embedding_cache_dir}")


if __name__ == "__main__":
    main()
