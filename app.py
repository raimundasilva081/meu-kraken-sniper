import time
import re
import socket
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Configuração agressiva de CORS para aceitar qualquer origem e os headers necessários
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

def sniper_engine(url_target):
    if not url_target.startswith(('http://', 'https://')):
        url_target = 'https://' + url_target

    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") # IMPORTANTE: Adicionado para evitar crash no Linux (Render)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
try:
        # No Docker do Render, o motor fica nesse caminho padrão:
        service = Service("/usr/bin/chromedriver") 
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        # Se não achar no caminho acima, tenta o modo automático padrão
        driver = webdriver.Chrome(options=chrome_options)
    
    res = {
        "target": url_target, "status": False, "domain": "", "ip": "", 
        "gates": [], "firewalls": [], "min_price": "N/A", "title": "", "error": ""
    }

    try:
        driver.get(url_target)
        time.sleep(5) 
        
        res["domain"] = urlparse(driver.current_url).netloc
        res["title"] = driver.title[:50]
        try: res["ip"] = socket.gethostbyname(res["domain"])
        except: res["ip"] = "Protegido/CDN"

        html_raw = driver.page_source.lower()
        
        # --- Lógica de Preço ---
        precos = re.findall(r'r\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2}))', html_raw)
        if precos:
            valores = [float(p.replace('.', '').replace(',', '.')) for p in precos]
            valores_reais = [v for v in valores if v > 0]
            if valores_reais:
                res["min_price"] = f"R$ {min(valores_reais):.2f}"
            else:
                res["min_price"] = "N/A (R$ 0,00)"

        # --- PALAVRAS-CHAVE ---
        buy_keywords = ["comprar", "adicionar", "quero este", "obter", "garantir", "reservar", "assinar", "matricula", "inscricao", "quero agora", "levar", "adquirir", "escolher", "selecionar", "comprar agora", "aproveitar oferta", "garantir vaga", "quero meu desconto", "comprar com desconto", "eu quero", "começar agora", "testar agora", "pegar meu", "acesso imediato", "baixar agora", "orderar", "fazer pedido", "adicionar a sacola", "botar no carrinho", "pague agora", "ir para oferta", "buy", "purchase", "add to cart", "add to bag", "get it", "order now", "subscribe", "enroll", "shop now", "secure checkout", "pay now", "proceed", "pick", "grab", "get access", "join now", "buy today", "add item", "select", "choose", "buy this", "add to basket", "go to shop", "order here", "take this", "buy now pay later", "get discount", "start trial", "download now", "add to order", "book now", "reserve", "secure seat", "buy ticket", "get copy", "quero comprar", "comprar", "añadir", "carrito", "bolsa", "suscribirse", "adquirir", "pago", "comprar ya", "obtener"]
        cart_keywords = ["ver carrinho", "ir para o carrinho", "minha sacola", "finalizar compra", "fechar pedido", "concluir pedido", "ir para o pagamento", "resumo do pedido", "ver pedido", "prosseguir", "continuar", "finalizar", "fechar compra", "pagamento seguro", "checkout", "ir para o caixa", "terminar pedido", "confirmar compra", "dados de pagamento", "preencher dados", "completar", "prosseguir para o checkout", "ver minha bolsa", "checkout agora", "finalizar agora", "ir para etapa final", "revisar pedido", "enviar pedido", "pagar com cartao", "pix agora", "gerar boleto", "proximo passo", "etapa de pagamento", "fechar carrinho", "concluir pagamento", "view cart", "go to checkout", "my bag", "shopping cart", "basket", "proceed to checkout", "checkout now", "view basket", "order summary", "continue to payment", "confirm order", "go to cart", "finish order", "to checkout", "secure payment", "make payment", "pay securely", "next step", "continue to checkout", "complete purchase", "review order", "place order", "to the cart", "open cart", "show bag", "buy now checkout", "fast checkout", "express checkout", "guest checkout", "login to pay", "continue as guest", "shipping details", "payment info", "ver carrito", "finalizar compra", "ir a la caja", "ver bolsa", "completar pedido", "pagar ahora"]

        # --- BANCOS DE DADOS REGEX ---
        gates_db = {"Mercado Pago": r"(mercadopago|mp-card-form|mp-credit-card|mp-checkout)", "Appmax": r"(appmax|checkout\.appmax|cdn\.appmax)", "Stripe": r"(stripe\.com|__stripe_orig|stripe-js|stripe-payments)", "PagSeguro": r"(pagseguro|pagbank-card|pagseguro\.uol)", "Pagar.me": r"(pagar\.me|pagarme-js|pagarme-checkout)", "Cielo": r"(cielo\.com\.br|cieloecommerce|buy-page-cielo)", "Rede": r"(userede|eredetreinamento|checkout-rede)", "Getnet": r"(getnet|checkout-getnet)", "Stone": r"(stone\.com\.br|stone-payments)", "Adiq": r"(adiq\.com\.br)", "SafraPay": r"(safrapay\.com\.br)", "Bin / First Data": r"(bin\.com\.br|firstdata)", "Vindi": r"(vindi\.com\.br|checkout-vindi|yapay)", "Iugu": r"(iugu\.com|iugu-js-checkout)", "Asaas": r"(asaas\.com/checkout)", "Zoop": r"(zoop\.com\.br|zoop-js)", "Ebanx": r"(ebanx|ebanx-checkout|ebanx-card)", "SuitPay": r"(suitpay\.com)", "EzzeBank": r"(ezzebank)", "Primepag": r"(primepag)", "CloudWalk / InfinitePay": r"(cloudwalk|infinitepay)", "Yampi": r"(yampi\.io/checkout|d\.yampi)", "Cartpanda": r"(cartpanda|checkout-cartpanda)", "Doppus": r"(doppus\.com)", "PerfectPay": r"(perfectpay\.com\.br)", "Braip": r"(checkout\.braip|braip\.com)", "Kiwify": r"(pay\.kiwify|kiwify\.com)", "Kirvano": r"(checkout\.kirvano)", "Ticto": r"(checkout\.ticto)", "Pepper": r"(checkout\.pepper)", "Greenn": r"(greenn\.com\.br)", "Hotmart": r"(pay\.hotmart|hotmart\.com)", "Eduzz / Blinket": r"(blinket\.com\.br|eduzz\.com)", "Monetizze": r"(checkout\.monetizze)", "PayPal Pro": r"(paypal\.com/sdk/js|paypal-checkout-card)", "Authorize.Net": r"(authorize\.net|anet-js)", "Braintree": r"(braintreegateway|braintree-js)", "Square": r"(squareup\.com|square-card-form)", "Adyen": r"(adyen\.com|adyen-checkout-card)", "Worldpay": r"(worldpay\.com|wp-payment)", "Checkout.com": r"(checkout\.com|frames-js)", "BlueSnap": r"(bluesnap\.com)", "Cybersource": r"(cybersource\.com)", "2Checkout": r"(2checkout\.com|verifone-checkout)", "FastSpring": r"(fastspring\.com)", "Paddle": r"(paddle\.com|paddle-checkout)", "Global Payments": r"(globalpaymentsinc)", "SagePay / Opayo": r"(sagepay\.com|opayo)", "Mollie": r"(mollie\.com)", "Skrill": r"(skrill\.com)", "Neteller": r"(neteller\.com)", "Payoneer": r"(payoneer\.com)", "Klarna": r"(klarna\.com)", "Elavon": r"(elavon\.com)", "NMI": r"(nmi\.com|networkmerchants)", "Shift4": r"(shift4\.com)", "CardConnect": r"(cardconnect\.com)", "Windcave": r"(windcave\.com)", "Moneris": r"(moneris\.com)", "Heartland": r"(heartlandpaymentsystems)", "TSYS": r"(tsys\.com)", "Adrepay": r"(adrepay)", "PayJunction": r"(payjunction)", "ProPay": r"(propay)", "Fiserv": r"(fiserv\.com)", "Paysafe": r"(paysafe\.com)", "Alipay": r"(alipay\.com)", "WeChat Pay": r"(wechat\.com)", "dLocal": r"(dlocal\.com)", "Kushki": r"(kushki\.com)", "PayU": r"(payu\.com)", "Eway": r"(eway\.com)", "Razorpay": r"(razorpay\.com)", "Paytm": r"(paytm\.com)", "Yookassa": r"(yookassa)", "CloudPayments": r"(cloudpayments)", "PayMaya": r"(paymaya)", "Omise": r"(omise\.co)", "Paymentwall": r"(paymentwall)", "Hipay": r"(hipay)", "Redsys": r"(redsys\.es)", "CCBill": r"(ccbill\.com)", "SegPay": r"(segpay\.com)", "RocketGate": r"(rocketgate\.com)", "Epoch": r"(epoch\.com)", "Probiller": r"(probiller\.com)", "Verotel": r"(verotel\.com)", "Mpay5": r"(mpay5)", "Centrobill": r"(centrobill)", "PaymentCloud": r"(paymentcloudinc)", "Instabill": r"(instabill)", "Durango Merchant": r"(durangomerchant)", "SMB Global": r"(smbglobal)", "PinPayments": r"(pinpayments)", "ClickBank": r"(clickbank)", "BuyGoods": r"(buygoods)", "Digistore24": r"(digistore24)", "MoonPay": r"(moonpay\.com)", "Simplex": r"(simplex\.com)", "Wyre": r"(sendwyre\.com)", "Banxa": r"(banxa\.com)", "CoinGate": r"(coingate\.com)", "Transak": r"(transak\.com)", "Upnid": r"(upnid\.com)", "PagHiper": r"(paghiper\.com)", "DigitalManager": r"(digitalmanager\.guru|dmguru)", "Hubla": r"(hubla\.com)", "TMB Educação": r"(tmbeducacao\.com\.br)", "Paggue": r"(paggue\.com)", "XPay": r"(xpay\.com\.br)", "Juno": r"(juno\.com\.br)", "Gerencianet / Efí": r"(gerencianet|sejaefi)", "PagaLeve": r"(pagaleve\.com\.br)", "PicPay": r"(picpay\.com)", "Ame Digital": r"(amedigital\.com)", "Safe2Pay": r"(safe2pay\.com\.br)", "GalaxPay": r"(galaxpay\.com\.br)", "Voluti": r"(voluti\.com\.br)", "OpenPix": r"(openpix\.com)", "Woovi": r"(woovi\.com)", "Pagae": r"(pagae\.com)", "Bcash": r"(bcash\.com\.br)", "MundiPagg": r"(mundipagg\.com)", "Amazon Pay": r"(amazonpay|amazon-pay)", "Google Pay": r"(google-pay|pay\.google\.com)", "Apple Pay": r"(apple-pay)", "Ingenico": r"(ingenico\.com)", "Bancard": r"(bancard\.com\.py)", "PagosOnline": r"(pagosonline\.com)", "Verifone": r"(verifone\.com)", "PayFast": r"(payfast\.co\.za)", "Monei": r"(monei\.com)", "Stax": r"(staxpayments\.com)", "Coinbase Commerce": r"(coinbase\.com/commerce)", "BitPay": r"(bitpay\.com)", "NowPayments": r"(nowpayments\.io)", "Binance Pay": r"(binance-pay|binance\.com)", "Crypto.com Pay": r"(crypto\.com/pay)", "OpenNode": r"(opennode\.com)", "GoCoin": r"(gocoin\.com)", "BTCPay": r"(btcpay)", "TripleA": r"(triple-a\.io)"}
        sec_db = {"Cloudflare (WAF)": r"(cloudflare|cf-ray|cf-cache|__cfduid|cf-quiet)", "Akamai (Kona)": r"(akamai|akamaighost|x-akamai|akamai-staging)", "AWS Shield/WAF": r"(aws-waf|awswaf|x-amz-cf|amazon-waf)", "Imperva (Incapsula)": r"(incapsula|visid_incap|_incap_)", "Sucuri": r"(sucuri|x-sucuri)", "F5 BIG-IP (ASM)": r"(f5-active|bigipserver|ts[a-z0-9]{8})", "Barracuda WAF": r"(barracuda|barra_counter)", "Citrix ADC (NetScaler)": r"(ns_cookietest|ns_session|citrix)", "Radware (AppWall)": r"(radware|x-rdwr)", "Fortinet (FortiWeb)": r"(fortiweb|fortinet)", "Check Point (SandBlast)": r"(checkpoint|x-chkp)", "ModSecurity": r"(mod_security|modsec)", "Azure WAF": r"(azure-waf|x-ms-request-id)", "Google Cloud Armor": r"(s_google_waf|x-cloud-trace-context)", "Fastly (WAF)": r"(fastly|x-fastly)", "Varnish (Shield)": r"(varnish|x-varnish)", "StackPath": r"(stackpath)", "DataDome": r"(datadome|dd-cookie)", "PerimeterX": r"(perimeterx|px-cdn|px-cookie)", "Human Security (WhiteOps)": r"(humansecurity|whiteops)", "Shape Security (F5)": r"(shapesecurity|sn_cookie)", "Kount (Fraud Prevention)": r"(kount|kaptcha)", "Distil Networks": r"(distil|x-distil)", "Kasada": r"(kasada|k-cookie)", "BotGuard": r"(botguard)", "Arkose Labs (FunCaptcha)": r"(arkoselabs|funcaptcha)", "GeeTest": r"(geetest|gt\.js)", "hCaptcha": r"(hcaptcha\.com|hcaptcha-token)", "Recaptcha V2/V3": r"(google\.com/recaptcha|g-recaptcha)", "Cloudflare Turnstile": r"(challenges\.cloudflare\.com|turnstile)", "Wordfence": r"(wordfence|wf-plugin)", "Imunify360": r"(imunify360)", "BitNinja": r"(bitninja)", "NinjaFirewall": r"(ninjafirewall)", "Cerber Security": r"(cerber-security)", "All In One WP Security": r"(aio-wp-security)", "SiteLock": r"(sitelock)", "Comodo WAF": r"(comodo-waf)", "SafeLine": r"(safeline)", "Chaitin": r"(chaitin)", "Bluetriangle": r"(btttag)", "Queue-it": r"(queue-it)", "KeyCDN": r"(keycdn)", "GoDaddy WAF": r"(secureserver\.net)", "BotX": r"(botx)", "Shield Security": r"(shield-security)", "F5 Silverline": r"(f5-silverline)", "Palo Alto WAF": r"(palo-alto-waf)", "Signal Sciences": r"(signalsciences)", "Wallarm": r"(wallarm)", "Sqreen": r"(sqreen)", "Reblaze": r"(reblaze)", "Indusface AppTrana": r"(apptrana)", "Prophaze": r"(prophaze)", "Rohde & Schwarz": r"(rohdeschwarz)", "Airlock WAF": r"(airlock-waf)", "Haltdos": r"(haltdos)", "NAXSI": r"(naxsi)", "DenyAll": r"(denyall)", "Sophos UTM": r"(sophos-utm)", "WatchGuard": r"(watchguard)", "SonicWall WAF": r"(sonicwall-waf)", "Kemp LoadMaster": r"(kemp-loadmaster)", "Snort IPS": r"(snort-ips)", "Suricata": r"(suricata)", "Fail2Ban": r"(fail2ban)", "Iptables / Netfilter": r"(netfilter)", "Cloudbric": r"(cloudbric)", "Aliyun WAF (Alibaba)": r"(aliyun-waf)", "Tencent WAF": r"(tencent-waf)", "Baidu Yunjiasu": r"(yunjiasu)"}

        # --- FLUXO DE NAVEGAÇÃO AGRESSIVA ---
        found_buy = False
        for kw in buy_keywords:
            try:
                btn = driver.find_element(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')] | //img[contains(@alt, '{kw}')]")
                driver.execute_script("arguments[0].click();", btn)
                found_buy = True
                time.sleep(5) 
                break
            except: continue

        if found_buy and "checkout" not in driver.current_url.lower():
            for c_kw in cart_keywords:
                try:
                    btn_c = driver.find_element(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{c_kw}')]")
                    driver.execute_script("arguments[0].click();", btn_c)
                    time.sleep(6) 
                    break
                except: continue

        # --- ANÁLISE FINAL DE CHECKOUT ---
        final_html = driver.page_source.lower()
        cookies = str(driver.get_cookies()).lower()
        
        res["gates"] = [n for n, p in gates_db.items() if re.search(p, final_html)]
        
        full_sec_text = final_html + cookies
        res["firewalls"] = [n for n, p in sec_db.items() if re.search(p, full_sec_text)]

        res["status"] = True

    except Exception as e:
        res["error"] = str(e)
    finally:
        driver.quit()
    return res

# --- ENDPOINT DA API ---
@app.route('/api/scan', methods=['POST'])
def scan_api():
    dados = request.get_json()
    urls = dados.get('urls')
    
    if not urls or not isinstance(urls, list):
        return jsonify({"status": False, "error": "Manda uma lista de URLs em 'urls'"}), 400

    start_time = time.time()
    
    # IMPORTANTE: No Render gratuito, max_workers=3 é o limite seguro. Mais que isso pode dar Out Of Memory.
    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados = list(executor.map(sniper_engine, urls))

    total_duration = round(time.time() - start_time, 2)
    
    return jsonify({
        "total_sites": len(urls),
        "duration": total_duration,
        "results": resultados
    })

# --- INICIALIZAÇÃO CORRETA PARA SERVIDOR ---
if __name__ == '__main__':
    # Modificado para host='0.0.0.0' para o Render conseguir expor a API para a internet
    app.run(host='0.0.0.0', port=5000)
