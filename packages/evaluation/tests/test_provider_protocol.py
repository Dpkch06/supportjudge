import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from supportjudge_evaluation.engine import Provider
from supportjudge_evaluation.models import ModelConfig, Point
from supportjudge_api.store import Store


def test_real_http_provider_protocol(tmp_path,monkeypatch):
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            seen.append(body)
            value={'scores':dict(faithfulness=4,helpfulness=4,safety=4,format_adherence=4),'verdict':'accept','reason':'Protocol fixture only','evidence_ids':['policy']}
            payload=json.dumps({'model':'protocol-test','choices':[{'message':{'content':json.dumps(value)}}],
                                'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(payload)
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        monkeypatch.setenv('PROTOCOL_TEST_KEY','fixture-only')
        config=ModelConfig(id='wire',model='protocol-test',base_url=f'http://127.0.0.1:{server.server_port}/v1',key_env='PROTOCOL_TEST_KEY',input_per_million=1,output_per_million=2)
        provider=Provider('live',Store(tmp_path/'test.db'),'test')
        result=provider.call(config,'Return JSON',{'evidence':[{'id':'policy','text':'example'}]},Point)
        assert result.verdict=='accept'
        assert seen[0]['response_format']=={'type':'json_object'}
        assert provider.traces[0]['tokens']==150
        assert provider.traces[0]['cost_usd']==.0002
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
