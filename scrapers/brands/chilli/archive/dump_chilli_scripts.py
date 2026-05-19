from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.chillisurfboards.com"
URL = "https://www.chillisurfboards.com/surfboards/detail.php?id=25279&direct=1&region=aus"

OUTPUT_FILE = Path("scrapers/brands/chilli/output/chilli_scripts_dump.txt")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
})

session.get(
    f"{BASE_URL}/changeregion.php?region=aus",
    timeout=(10, 30),
)

response = session.get(
    URL,
    timeout=(10, 30),
)

soup = BeautifulSoup(response.text, "html.parser")

blocks = []

for idx, script in enumerate(soup.find_all("script")):

    src = script.get("src")

    if src:

        blocks.append(
            "\n" + "=" * 100 + "\n" +
            f"SCRIPT SRC {idx}\n" +
            "=" * 100 + "\n" +
            src
        )

    else:

        text = script.get_text("\n", strip=True)

        if any(
            keyword in text.lower()
            for keyword in [
                "graphql",
                "json",
                "variant",
                "dimension",
                "volume",
                "length",
                "fetch",
                "ajax",
                "api",
                "board",
                "model",
            ]
        ):

            blocks.append(
                "\n" + "=" * 100 + "\n" +
                f"INLINE SCRIPT {idx}\n" +
                "=" * 100 + "\n" +
                text[:12000]
            )

OUTPUT_FILE.write_text(
    "\n".join(blocks),
    encoding="utf-8",
)

print("Scripts found:", len(blocks))
print("Saved:", OUTPUT_FILE)
