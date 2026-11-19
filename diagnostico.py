"""Mede o ambiente em que é executado e grava um JSON para o relatório."""

import argparse
import json
import platform
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import psutil


def diagnosticar(url, pid=None):
    tempos = []
    tamanho_json = 0
    for _ in range(50):
        inicio = time.perf_counter()
        with urllib.request.urlopen(url + "/api/estado", timeout=10) as resposta:
            tamanho_json = len(resposta.read())
        tempos.append((time.perf_counter() - inicio) * 1000)
    processador = platform.processor()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        processador = next((l.split(":", 1)[1].strip() for l in cpuinfo.read_text().splitlines() if l.startswith("model name")), processador)
    processo = psutil.Process(pid) if pid else None
    return {
        "data_utc": datetime.now(timezone.utc).isoformat(),
        "ambiente": "Ambiente de execução do diagnóstico",
        "cpu": processador, "arquitetura": platform.machine(),
        "sistema": platform.platform(), "python": platform.python_version(),
        "cpus_logicas_visiveis": psutil.cpu_count(),
        "ram_visivel_gib": round(psutil.virtual_memory().total / 1024**3, 2),
        "rss_servidor_mib": round(processo.memory_info().rss / 1024**2, 2) if processo else None,
        "latencia_media_ms": round(statistics.mean(tempos), 3),
        "latencia_p95_ms": round(sorted(tempos)[47], 3),
        "consultas": 50, "tamanho_resposta_bytes": tamanho_json,
        "url_testada": url,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--saida", type=Path, default=Path("dados/diagnostico_local.json"))
    args = parser.parse_args()
    resultado = diagnosticar(args.url, args.pid)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
