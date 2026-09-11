"""Prepare the pinned Windows CPU verifier runtime and model (no document data)."""
import hashlib
import shutil
from pathlib import Path
from zipfile import ZipFile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1] / ".cache" / "verifier"
ASSETS = [
    ("llama-b10809-bin-win-cpu-x64.zip",
     "https://github.com/ggml-org/llama.cpp/releases/download/b10809/llama-b10809-bin-win-cpu-x64.zip",
     "9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5"),
    ("Qwen_Qwen3-4B-Instruct-2507-Q3_K_S.gguf",
     "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q3_K_S.gguf",
     "68e5c8cb8ac33cb5b86c1dc31885a772782b42699d144fcfbe353489d9b289db"),
]


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, url, expected in ASSETS:
        target = ROOT / name
        if target.exists() and digest(target) == expected:
            print(f"Verified cached {name}", flush=True)
            continue
        temporary = target.with_suffix(target.suffix + ".partial")
        required = 1886997216 if name.endswith(".gguf") else 18407457
        offset = temporary.stat().st_size if temporary.exists() else 0
        if shutil.disk_usage(ROOT).free < required - offset + 256 * 1024 * 1024:
            raise RuntimeError("Insufficient free disk space for download plus a 256 MiB reserve.")
        print(f"Downloading {name} from byte {offset}", flush=True)
        request = Request(url, headers={"Range": f"bytes={offset}-"})
        with urlopen(request, timeout=60) as response:
            if response.status == 206:
                if not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise RuntimeError("Unexpected download range")
                mode = "ab"
            elif response.status == 200:
                mode, offset = "wb", 0
            else:
                raise RuntimeError("Unexpected download response")
            report_at = offset + 64 * 1024 * 1024
            with temporary.open(mode) as destination:
                while block := response.read(1024 * 1024):
                    destination.write(block)
                    offset += len(block)
                    if offset >= report_at:
                        print(f"Downloaded {offset // (1024 * 1024)} MiB", flush=True)
                        report_at = offset + 64 * 1024 * 1024
        if digest(temporary) != expected:
            raise RuntimeError(f"Checksum mismatch for {name}; file will not be used.")
        temporary.replace(target)
        print(f"Verified {name}", flush=True)
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    with ZipFile(ROOT / ASSETS[0][0]) as archive:
        for member in archive.namelist():
            if not (runtime / member).resolve().is_relative_to(runtime.resolve()):
                raise RuntimeError("Unexpected archive path")
        archive.extractall(runtime)
    print(f"Ready. Runtime: {runtime}", flush=True)


if __name__ == "__main__":
    main()
