# encoding:utf-8

from channel.http.http_channel import HttpChannel
from channel.wechat.wechat_com_channel import WechatEnterpriseChannel
from channel.wechat.wechat_channel import WechatChannel
import plugins
from plugins import *
from common import functions
from config import channel_conf
from config import channel_conf_val
from common import const
from common.log import logger
import uuid
import json
from plugins import mj_global
import time
from config import conf
import plugins
from plugins import *
from common.log import logger

import requests


@plugins.register(name="MJWXCom", desire_priority=100, hidden=True, desc="A MJ plugin that create images from model", version="0.1", author="Martins")
class MJWXCom(Plugin):
    def __init__(self):
        super().__init__()
        self.channel_types = {
                              WechatEnterpriseChannel:const.WECHAT_COM,
                              WechatChannel: const.WECHAT}
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.handle_query


    def get_events(self):
        return self.handlers



    def butt_discord(self, prompt):
            prompt = prompt.replace('_', ' ')
            prompt = " ".join(prompt.split())
            prompt = prompt.lower()
            data=dict(type='imagine', prompt=prompt, msgId='wx__' + str(uuid.uuid4()))
            requests.post('###', data=json.dumps(data))
            while True:
                l = mj_global.all()
                if len(l) == 0:
                    time.sleep(1)
                else:
                   result = l[0]['imageUrl']
                   break

            return result

    
    def handle_query(self, e_context: EventContext):
        
        channel = e_context['channel']
        channel_type = self.channel_types.get(type(channel), None)
        logger.info(f'handle_query e_context:{e_context} ')
        query = e_context['context']
        logger.info(f'handle_query query:{query}')
        if (query):
            img_match_prefix = functions.check_prefix(
                query, channel_conf_val(channel_type, 'image_create_prefix'))
            logger.info(f'handle_query img_match_prefix:{img_match_prefix}')
            query = query.split(img_match_prefix, 1)[1].strip()
            e_context['args']['type'] = 'IMAGE_CREATE'
            e_context['reply'] = 'https://cong-img.oss-cn-hangzhou.aliyuncs.com/mj/dr_fd5d2932-317f-4f21-ab44-4c7d1a33f42a.png'
            if (channel_type == const.WECHAT or channel_type == const.WECHAT_COM):
                channel._do_send_img(
                    query, e_context['args'])
                e_context.action = EventAction.BREAK_PASS
            else:
                e_context.action = EventAction.CONTINUE
            
        return e_context

   

    def send_images(self, e_context: EventContext):
        channel = e_context['channel']
        method = self.handles.get(type(channel), None)
        if (method):
            e_context = method(e_context)
        e_context.action = EventAction.BREAK_PASS  # 事件结束，不再给下个插件处理，不交付给默认的事件处理逻辑
        return e_context