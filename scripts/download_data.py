"""
Baixa os arquivos do Inside Airbnb para data/raw/.

Uso:
    python scripts/download_data.py
    python scripts/download_data.py --snapshot 2025-06-21
    python scripts/download_data.py --country brazil --region rj --city rio-de-janeiro

A data do snapshot muda a cada nova versão publicada. Consulte a data
disponível em https://insideairbnb.com/get-the-data/ e atualize SNAPSHOT abaixo
(ou passe --snapshot na linha de comando).

Dados: Inside Airbnb (https://insideairbnb.com) - licença CC BY 4.0.
"""

import argparse
import sys
import urllib.request
from pathlib import Path

# ---- Configuração padrão -------------------------------------------------
COUNTRY = "brazil"
REGION = "rj"
CITY = "rio-de-janeiro"
SNAPSHOT = "AAAA-MM-DD"  # <- substitua pela data do snapshot escolhido

BASE_URL = "https://data.insideairbnb.com"

# arquivo remoto -> nome local
FILES = {
    "data/listings.csv.gz": "listings.csv.gz",
    "data/calendar.csv.gz": "calendar.csv.gz",
    "data/reviews.csv.gz": "reviews.csv.gz",
    "visualisations/neighbourhoods.csv": "neighbourhoods.csv",
}

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def download(url: str, dest: Path, force: bool = False) -> None:
    if dest.exists() and not force:
        print(f"[ok] {dest.name} já existe, pulando (use --force para baixar de novo)")
        return

    print(f"[..] baixando {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            while chunk := resp.read(1024 * 1024):
                out.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r     {done / total:6.1%} de {total / 1e6:.1f} MB", end="")
        print()
        tmp.replace(dest)
        print(f"[ok] salvo em {dest}")
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"falha ao baixar {url}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Baixa dados do Inside Airbnb")
    parser.add_argument("--country", default=COUNTRY)
    parser.add_argument("--region", default=REGION)
    parser.add_argument("--city", default=CITY)
    parser.add_argument("--snapshot", default=SNAPSHOT, help="data no formato AAAA-MM-DD")
    parser.add_argument("--force", action="store_true", help="baixa mesmo se o arquivo existir")
    args = parser.parse_args()

    if args.snapshot == "AAAA-MM-DD":
        print(
            "Defina a data do snapshot (SNAPSHOT no script ou --snapshot). "
            "Veja as datas em https://insideairbnb.com/get-the-data/"
        )
        return 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{BASE_URL}/{args.country}/{args.region}/{args.city}/{args.snapshot}"

    errors = 0
    for remote, local in FILES.items():
        try:
            download(f"{base}/{remote}", RAW_DIR / local, force=args.force)
        except RuntimeError as exc:
            print(f"[erro] {exc}")
            errors += 1

    if errors:
        print(f"\n{errors} arquivo(s) falharam. Confira a data do snapshot e a cidade.")
        return 1

    print(f"\nDownload concluído. Snapshot: {args.snapshot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
