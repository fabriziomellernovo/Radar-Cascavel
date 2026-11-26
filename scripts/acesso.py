import time, json, urllib.request, urllib.parse, urllib.robotparser
BASE="https://sapl.cascavel.pr.leg.br"
AGENT="Radar-Cascavel/1.1 (+https://github.com/fabriziomellernovo/Radar-Cascavel)"
last=0
robots=None
class AccessStopped(RuntimeError): pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise AccessStopped("Redirecionamento não autorizado; coleta interrompida")
opener=urllib.request.build_opener(NoRedirect())
def request(url,accept):
    global last
    u=urllib.parse.urlsplit(url)
    if u.scheme!="https" or u.netloc!="sapl.cascavel.pr.leg.br": raise AccessStopped("Fonte não autorizada")
    time.sleep(max(0,3-(time.monotonic()-last)))
    try:
        with opener.open(urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":accept}),timeout=40) as f:
            return f.read()
    except Exception as e:
        raise AccessStopped("Acesso interrompido: "+str(e)) from e
    finally:
        last=time.monotonic()
def get(url):
    global robots
    if robots is None:
        robots=urllib.robotparser.RobotFileParser()
        robots.parse(request(BASE+"/robots.txt","text/plain").decode("utf-8").splitlines())
    if not robots.can_fetch(AGENT,url): raise AccessStopped("robots.txt não permite coleta")
    delay=robots.crawl_delay(AGENT) or robots.crawl_delay("*") or 0
    rate=robots.request_rate(AGENT) or robots.request_rate("*")
    if rate: delay=max(delay,rate.seconds/rate.requests)
    time.sleep(max(0,delay-(time.monotonic()-last)))
    return json.loads(request(url,"application/json"))
