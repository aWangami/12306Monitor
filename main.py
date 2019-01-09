#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import time
import json
import random
import requests
try:
    import win32gui
    import win32con
except Exception as e:
    print(u'请执行`pip install pywin32`')

class Struct:
    def __init__(self, entries):
        self.__dict__.update(entries)

def getConfigFile():
    scriptFile = sys.argv[0]
    return os.path.join(os.path.split(os.path.realpath(scriptFile))[0], 'config.json')

_GLOBAL = Struct(json.load(open(getConfigFile())))

class Notifier(object):
    def important(self, msg):
        isPush = False
        if len(self.dingTokenListImportant) != 0:
            isPush = True
            result = self.pushToDingDing(msg, self.dingTokenListImportant)
            print(u'[推送消息] %s' % (list(result)))
        if self.enableWebHook:
            isPush = True
            result = self.runWebHook(msg)
            print(u'[推送消息] %s' % (list(result)))
        if not isPush:
            print(u'[警告] 没有找到推送方式，请检查config.json文件')

    def setDingTokenListImportant(self, tokenList):
        self.dingTokenListImportant = tokenList

    def notify(self, msg):
        if len(self.dingTokenListVerbose) != 0:
            self.pushToDingDing(msg, self.dingTokenListVerbose)

    def setDingTokenListVerbose(self, tokenList):
        self.dingTokenListVerbose = tokenList

    def pushToDingDing(self, msg, tokenList):
        token = tokenList[random.randint(0, len(tokenList) - 1)]
        return self.pushToDingDingInner(token, msg)

    def pushToDingDingInner(self, token, msg):
        reqData = {'msgtype': 'text','text': {'content': msg}}
        url = 'https://oapi.dingtalk.com/robot/send?access_token=%s' % (token)
        try:
            resp = requests.post(url = url, data = json.dumps(reqData, separators=(',', ':')), headers = {'Content-Type': 'application/json'}, verify = False)
            return True, resp.text
        except Exception as e:
            return False, e

    def setEnableWebHook(self, enable):
        self.enableWebHook = enable

    def setWebHookUrl(self, webhook):
        self.webhook = webhook

    def setWebHookType(self, method):
        self.webhookType = method

    def setWebHookData(self, webhookData):
        self.webhookData = webhookData

    def setWebHookDataType(self, webhookDataType):
        self.webhookDataType = webhookDataType

    def fitMessage(self, data, message):
        for key in data:
            value = data[key]
            if isinstance(value, dict):
                data[key] = self.fitMessage(value, message)
            else:
                value = value.replace(u'$message', message)
                data[key] = value
        return data

    def runWebHook(self, message):
        try:
            webhook = self.webhook.replace(u'$message', message)
            webhookData = self.fitMessage(self.webhookData, message)
            if self.webhookType == 'GET':
                resp = requests.get(url = webhook, verify = False)
                return True, resp.text
            elif self.webhookType == 'POST':
                if self.webhookDataType == 'json':
                    resp = requests.post(url = webhook, data = json.dumps(webhookData, separators=(',', ':')), headers = {'Content-Type': 'application/json'}, verify = False)
                else:
                    resp = requests.post(url = webhook, data = webhookData, verify = False)
                return True, resp.text
            return False, u'ErrorMethod'
        except Exception as e:
            return False, e

class Monitor(object):
    def __init__(self, handler, monitorWord = [], gohomeWord = [], debug = True):
        self.handler = handler
        self.debug = debug
        self.monitorWord = monitorWord
        self.gohomeWord = gohomeWord

    def run(self, notifier):
        readList = set()
        while True:
            length = 1024
            buffer = '0' * length
            win32gui.SendMessage(self.handler, win32con.WM_GETTEXT, length, buffer)
            headLine = buffer.split('\n')[0]
            headLine = headLine.decode(u'gb2312')
            if headLine not in readList:
                if self.debug:
                    print(headLine)
                for word in self.monitorWord:
                    if word in headLine:
                        notifier.notify(headLine)
                for word in self.gohomeWord:
                    if word in headLine:
                        notifier.important(headLine)
                if len(readList) > 100:
                    readList = set()
                readList.add(headLine)
            time.sleep(_GLOBAL.interval)

class MonitorWrapper(object):
    def __init__(self):
        self.notifier = Notifier()
        self.notifier.setDingTokenListVerbose(_GLOBAL.dingTokenListVerbose)
        self.notifier.setDingTokenListImportant(_GLOBAL.dingTokenListImportant)
        print(u'[调试] GET: %s, POST: %s' % (_GLOBAL.enableGetWebHook, _GLOBAL.enablePostWebHook))
        if _GLOBAL.enableGetWebHook:
            self.notifier.setEnableWebHook(True)
            self.notifier.setWebHookUrl(_GLOBAL.getWebHook)
            self.notifier.setWebHookType('GET')
        else:
            self.notifier.setEnableWebHook(False)
        if _GLOBAL.enablePostWebHook:
            self.notifier.setEnableWebHook(True)
            self.notifier.setWebHookUrl(_GLOBAL.postWebHook)
            self.notifier.setWebHookType('POST')
            self.notifier.setWebHookData(_GLOBAL.postWebHookData)
            self.notifier.setWebHookDataType(_GLOBAL.postWebHookType)
        else:
            self.notifier.setEnableWebHook(False)

    def findWindow(self):
        handlerList = []     
        def callback(hwnd, mouse):
            if win32gui.IsWindow(hwnd):
                title = win32gui.GetWindowText(hwnd)
                title = title.decode(u'gb2312')
                for word in [u'12306分流抢票']:
                    if word in title:
                        handlerList.append((hwnd, title))
        win32gui.EnumWindows(callback, 0)
        return handlerList

    def findOutputSubWindow(self, handler):
        handlerList = [handler]
        def callbackWindow(hwnd, param):
            if hwnd == 0:
                return
            text = win32gui.GetWindowText(hwnd)
            text = text.decode(u'gb2312')
            if u'输出区' in text:
                handlerList.append(hwnd)
        def callbackEdit(hwnd, param):
            if hwnd == 0:
                return
            clazz = win32gui.GetClassName(hwnd)
            if u'EDIT' in clazz:
                handlerList.append(hwnd)
        hwndChildList = []
        win32gui.EnumChildWindows(handlerList[-1], callbackWindow, hwndChildList)
        win32gui.EnumChildWindows(handlerList[-1], callbackEdit, hwndChildList)
        if len(handlerList) == 3:
            return handlerList[-1]
        return 0

    def start(self, handler):
        handler = self.findOutputSubWindow(handler)
        if handler == 0:
            print(u'[错误] 没有找到对应的窗口')
            return
        print(u'[提示] 监控开始')
        monitor = Monitor(handler, _GLOBAL.monitorWord, _GLOBAL.gohomeWord, True)
        monitor.run(self.notifier)

    def run(self):
        handlerList = self.findWindow()
        if len(handlerList) == 0:
            print(u'[错误] 没有找到相关窗口')
        elif len(handlerList) == 1:
            self.start(handlerList[0][0])
        else:
            print(u'提示] 找到多个窗口')
            for index in range(0, len(handlerList)):
                handler, title = handlerList[index]
                print(u'[%s] %s | %s' % (index, handler, title))
            index = raw_input(u'请选择: '.encode('gbk'))
            index = int(index)
            self.start(handlerList[index][0])

    def test(self):
        external = ''
        if _GLOBAL.enablePostWebHook and _GLOBAL.postWebHook.endswith('073af254'):
            external = u' (%s)'
            read = os.popen('git config user.email')
            read = read.read()
            read = read.strip()
            external = external % (read)
        self.notifier.important(u'测试通知，收到表示通知正常，可以开始监控抢票啦%s' % (external))

if __name__ == "__main__":
    MonitorWrapper().run()
