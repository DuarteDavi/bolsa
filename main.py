from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
import os

app = FastAPI(title="BetBra Exchange API")

# Permite que o frontend converse com o backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCHANGE_BASE = "https://mexchange-api.betbra.bet.br/api"
# Cole seus cookies atualizados aqui
COOKIES_RAW = """BIAB_LANGUAGE=PT_BR; BIAB_TZ=180; C_U_I=; _fbp=fb.2.1775489754036.902337090260769516; _ga=GA1.1.884168629.1775489754; _tt_enable_cookie=1; _ttp=01KNHPZ94J9R5PXQ518PB36RQP_.tt.2; _sp_srt_ses.241e=*; FPID=FPID2.3.Mb9mWCukYi9PCMjqYazUAC73%2FnvZ1aKYSUuLOxXbZ4E%3D.1775489754; FPLC=DfHD8FkJmtGkv%2BVSJbPq8m5bx5TTW0m%2BWva%2FQZZxvkI9IYhPnqRpA9eYa43kkfVs3TDX%2Fv7luuFgGm41UYdxTkpwn6cqsJOrv%2BoomNus1UI0m18TN8ffDOvqWRCMAw%3D%3D; FPAU=1.3.1466548169.1775489753; cf_clearance=HxJfkgE6r2_sfM_cr_DY9nFdLUWN7Gw8dcMuzzyCQyQ-1775492386-1.2.1.1-ylzXjqzuLh8FQxIFDGGnmyMQdKQAPj8ydmtKRxUExUL53crpzUQ8c7TLrpNer.gFHcg9U95UBBRYxtfDeMP_tk0po.WpeHM39IxxHbZn6HmgQisC4C7JXp63Dr4iQie0HPnFO.ShqcdeiG2R9Z3hYl5BtoNQ8Ww2wQlNNUpfmoMvs7830fx2wPofhAbTa99SDcvtnPsx_fY0JhU53joa7LsVputBRlr75EO0PvjqqjA.pTHq.0Fjv3May65aPmc_qhOqNXQNgjmijBTMFVNWZ5M1MH5YrJBOm9VwCV0pUMi_d.cLjzjShBPewAUgFgQe6te7yzLpkBSoLBy0DajeKg; _ga_8YSC4LQ18Z=GS2.1.s1775489754$o1$g1$t1775492468$j57$l0$h1641166552$deEsoUjfawIQ8Fh-OPLwr1MEuVkeMvbNgWQ; _sp_srt_id.241e=c41052b3-4629-41a5-9c1d-aa511305da86.1775489755.1.1775492469..1fd9ab2f-600d-47e5-b542-d75342b6f6e2....0; ttcsid=1775489754265::yA8l-IiwDRZd143qsH29.1.1775492469112.0::1.2713104.2714466::2518586.4.82.35::1759737.9.0; ttcsid_D4RH41JC77U321H5F03G=1775489754264::xCZn-77OhHQhHiyimWtA.1.1775492469112.1; ttcsid_D4RHBNBC77UET7S4G9SG=1775489754266::DjbNHRIB1p7jGcIe2vb1.1.1775492469112.1"""

def parse_cookies(raw):
    return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}

def get_exchange_games():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    })
    s.cookies.update(parse_cookies(COOKIES_RAW))
    
    agora = int(time.time())
    daqui_a_3_dias = agora + (3 * 24 * 60 * 60)
    url = f"{EXCHANGE_BASE}/events?offset=0&per-page=100&after={agora}&before={daqui_a_3_dias}&sport-ids=15&sort-by=volume&sort-direction=desc"
    
    try:
        r = s.get(url, timeout=10)
        if r.status_code != 200:
            return {"error": f"API retornou {r.status_code}"}
            
        data = r.json()
        items = data if isinstance(data, list) else data.get("events", [])
        
        jogos_limpos = []
        for jogo in items:
            if not isinstance(jogo, dict): continue
            
            mercados = [m for m in jogo.get("markets", []) if m.get("market-type") == "one_x_two"]
            odds_runners = []
            
            if mercados:
                for runner in mercados[0].get("runners", []):
                    backs = [p.get("decimal-odds") for p in runner.get("prices", []) if p.get("side") == "back"]
                    lays = [p.get("decimal-odds") for p in runner.get("prices", []) if p.get("side") == "lay"]
                    
                    odds_runners.append({
                        "nome": runner.get("name"),
                        "back": max(backs) if backs else "-",
                        "lay": min(lays) if lays else "-"
                    })
            
            # Pega o nome do campeonato das meta-tags
            liga = "Desconhecida"
            for tag in jogo.get("meta-tags", []):
                if tag.get("type") == "COMPETITION":
                    liga = tag.get("name")
            
            jogos_limpos.append({
                "id": jogo.get("id"),
                "jogo": jogo.get("name"),
                "liga": liga,
                "data": jogo.get("start"),
                "ao_vivo": jogo.get("in-running-flag", False),
                "volume": round(jogo.get("volume", 0), 2),
                "odds": odds_runners
            })
            
        return {"games": jogos_limpos}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/games")
def api_games():
    return get_exchange_games()

@app.get("/")
def serve_frontend():
    # Lê o arquivo index.html que vamos criar e envia pro navegador
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())