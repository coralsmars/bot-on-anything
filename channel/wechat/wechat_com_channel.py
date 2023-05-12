#!/usr/bin/env python
# -*- coding=utf-8 -*-
"""
@time: 2023/4/10 22:24
@Project ：bot-on-anything
@file: wechat_com_channel.py

"""
import requests,io
from channel.channel import Channel
from concurrent.futures import ThreadPoolExecutor
from common.log import logger
from config import *
from common import const
import uuid
from plugins.mj import mj_global
from plugins.plugin_manager import *
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise import WeChatClient
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.enterprise import parse_message
from flask import Flask, request, abort

thread_pool = ThreadPoolExecutor(max_workers=8)
app = Flask(__name__)

def download_image(image_url, file_name):
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        try:

            with open(file_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return True
        except Exception as e:
            log.error(str(e), exc_info=True)
        print("图片已保存到本地：", file_name)
    return False


@app.route('/wechat', methods=['GET', 'POST'])
def handler_wechat_msg():
    return WechatEnterpriseChannel().handle()

@app.route('/mj', methods=['POST'])
def handler_mj_msg():
     result = request.get_json()
     msgId=result['msgId']
     if msgId.startswith('wx__'):
        mj_global.put(msgId, result)

     


_conf = conf().get("channel").get("wechat_com")


class WechatEnterpriseChannel(Channel):



    def __init__(self):
        self.CorpId = _conf.get('wechat_corp_id')
        self.Secret = _conf.get('secret')
        self.AppId = _conf.get('appid')
        self.TOKEN = _conf.get('wechat_token')
        self.EncodingAESKey = _conf.get('wechat_encoding_aes_key')
        self.crypto = WeChatCrypto(self.TOKEN, self.EncodingAESKey, self.CorpId)
        self.client = WeChatClient(self.CorpId, self.Secret, self.AppId)

    def startup(self):
        # start message listener
        app.run(host='0.0.0.0', port=_conf.get('port'))

    def send(self, receiver, econtext, reply):
       
        msg_type = reply.get('type', 'text')
        
        #logger.info('[WXCOM] sendMsg={}, receiver={} msg_type {}'.format(msg, receiver, msg_type))
        if msg_type == 'IMAGE_CREATE':
            image_url = reply['image_url']
            file_name = os.getcwd() + '/' + str(uuid.uuid4()) + '.png'
            if download_image(image_url=image_url, file_name=file_name):
                media_id = None
                with open(file_name, 'rb+') as f:
                    data = self.client.media.upload('image', f)
                    logger.info(f'json-data:{data}')
                    media_id = data.get('media_id', None)
                if media_id is not None:
                    self.client.message.send_image(self.AppId, receiver, media_id)
                os.remove(file_name)
        else:  
            msg = econtext['text']
            self.client.message.send_text(self.AppId, receiver, msg)

    def _do_send(self, query, reply_user_id):
        try:
            if not query:
                return
            context = dict()
            context['from_user_id'] = reply_user_id
            e_context = PluginManager().emit_event(EventContext(Event.ON_HANDLE_CONTEXT, {
                'channel': self, 'context': query,  "args": context}))
            reply = e_context.econtext['context']
            
            if not e_context.is_pass():
                reply = super().build_reply_content(e_context["econtext"], e_context["args"])
                e_context = PluginManager().emit_event(EventContext(Event.ON_DECORATE_REPLY, {
                    'channel': self, 'context': context, 'reply': reply, "args": e_context["args"]}))
                reply = e_context['reply']
                if reply:
                    self.send(reply_user_id, e_context["econtext"], e_context["reply"])
            else:
                reply = e_context['reply']
                if reply:
                    self.send(reply_user_id, e_context["econtext"], e_context["reply"])
        except Exception as e:
            logger.exception(e)

    

    def handle(self):
        query_params = request.args
        signature = query_params.get('msg_signature', '')
        timestamp = query_params.get('timestamp', '')
        nonce = query_params.get('nonce', '')
        if request.method == 'GET':
            # 处理验证请求
            echostr = query_params.get('echostr', '')
            try:
                echostr = self.crypto.check_signature(signature, timestamp, nonce, echostr)
            except InvalidSignatureException:
                abort(403)
            print(echostr)
            return echostr
        elif request.method == 'POST':
            try:
                message = self.crypto.decrypt_message(
                    request.data,
                    signature,
                    timestamp,
                    nonce
                )
            except (InvalidSignatureException, InvalidCorpIdException):
                abort(403)
            msg = parse_message(message)
            if msg.type == 'text':
                thread_pool.submit(self._do_send, msg.content, msg.source)
            else:
                reply = 'Can not handle this for now'
                # 未能处理的消息或菜单事件暂不做响应优化用户体验
                # self.client.message.send_text(self.AppId, msg.source, reply)
            return 'success'
