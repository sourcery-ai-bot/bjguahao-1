#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北京市预约挂号统一平台
"""

import os
import sys
import re
import json
import time
import datetime
import logging
import base64
from lib.prettytable import PrettyTable

if sys.version_info.major != 3:
    logging.error("请在python3环境下运行本程序")
    sys.exit(-1)

try:
    import requests
except ModuleNotFoundError as e:
    logging.error("请安装python3 requests")
    sys.exit(-1)

from browser import Browser

try:
    import yaml
except ModuleNotFoundError as e:
    logging.error("请安装python3 yaml模块")
    sys.exit(-1)


class Config(object):

    def __init__(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as yaml_file:
                data = yaml.load(yaml_file)
                debug_level = data["DebugLevel"]
                if debug_level == "critical":
                    self.debug_level = logging.CRITICAL

                elif debug_level == "debug":
                    self.debug_level = logging.DEBUG
                elif debug_level == "error":
                    self.debug_level = logging.ERROR
                elif debug_level == "info":
                    self.debug_level = logging.INFO
                elif debug_level == "warning":
                    self.debug_level = logging.WARNING
                logging.basicConfig(level=self.debug_level,
                                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                                    datefmt='%a, %d %b %Y %H:%M:%S')

                self.mobile_no = data["username"]
                self.password = data["password"]
                self.date = data["date"]
                self.hospital_id = data["hospitalId"]
                self.department_id = data["departmentId"]
                self.duty_code = data["dutyCode"]
                self.patient_name = data["patientName"]
                self.doctorName = data["doctorName"]
                self.patient_id = int()
                try:
                    self.useIMessage = data["useIMessage"]
                except KeyError:
                    self.useIMessage = "false"
                try:
                    self.useQPython3 = data["useQPython3"]
                except KeyError:
                    self.useQPython3 = "false"
                #
                logging.info("配置加载完成")
                logging.debug(f"手机号:{str(self.mobile_no)}")
                logging.debug(f"挂号日期:{str(self.date)}")
                logging.debug(f"医院id:{str(self.hospital_id)}")
                logging.debug(f"科室id:{str(self.department_id)}")
                logging.debug(f"上午/下午:{str(self.duty_code)}")
                logging.debug(f"就诊人姓名:{str(self.patient_name)}")
                logging.debug(f"所选医生:{str(self.doctorName)}")
                logging.debug(f"使用mac电脑接收验证码:{self.useIMessage}")
                logging.debug(f"是否使用 QPython3 运行本脚本:{self.useQPython3}")

                if not self.date:
                    logging.error("请填写挂号时间")
                    exit(-1)

        except Exception as e:
            logging.error(repr(e))
            sys.exit()


class Guahao(object):
    """
    挂号
    """

    def __init__(self, config_path="config.yaml"):
        self.browser = Browser()
        self.dutys = ""
        self.refresh_time = ''

        self.login_url = "http://www.bjguahao.gov.cn/quicklogin.htm"
        self.send_code_url = "http://www.bjguahao.gov.cn/v/sendorder.htm"
        self.get_doctor_url = "http://www.bjguahao.gov.cn/dpt/partduty.htm"
        self.confirm_url = "http://www.bjguahao.gov.cn/order/confirm.htm"
        self.patient_id_url = "http://www.bjguahao.gov.cn/order/confirm/"
        self.department_url = "http://www.bjguahao.gov.cn/dpt/appoint/"

        self.config = Config(config_path)                       # config对象
        if self.config.useIMessage == 'true':
            # 按需导入 imessage.py
            import imessage
            self.imessage = imessage.IMessage()
        else:
            self.imessage = None

        if self.config.useQPython3 == 'true':
            try: # Android QPython3 验证
                # 按需导入 qpython3.py
                import qpython3
                self.qpython3 = qpython3.QPython3()
            except ModuleNotFoundError:
                self.qpython3 = None
        else:
            self.qpython3 = None

    def is_login(self):

        logging.info("开始检查是否已经登录")
        hospital_id = self.config.hospital_id
        department_id = self.config.department_id
        duty_code = self.config.duty_code
        duty_date = self.config.date

        payload = {
            'hospitalId': 142,
            'departmentId': 200039602,
            'dutyCode': 1,
            'dutyDate': time.strftime("%Y-%m-%d"),
            'isAjax': True
        }

        response = self.browser.post(self.get_doctor_url, data=payload)
        try:
            data = json.loads(response.text)
            if data["code"] == 200 and data["msg"] == "OK":
                logging.debug(f"response data:{response.text}")
                return True
            else:
                logging.debug("response data: HTML body")
                return False
        except Exception as e:
            logging.error(e)
            return False

    def auth_login(self):
        """
        登陆
        """
        try:
            # patch for qpython3
            cookies_file = os.path.join(
                os.path.dirname(sys.argv[0]), f".{self.config.mobile_no}.cookies"
            )
            self.browser.load_cookies(cookies_file)
            if self.is_login():
                logging.info("cookies登录成功")
                return True
        except Exception as e:
            pass

        logging.info("cookies登录失败")
        logging.info("开始使用账号密码登陆")
        password = self.config.password
        mobile_no = self.config.mobile_no
        payload = {
            'mobileNo': base64.b64encode(mobile_no.encode()),
            'password': base64.b64encode(password.encode()),
            'yzm': '',
            'isAjax': True,
        }
        response = self.browser.post(self.login_url, data=payload)
        logging.debug(f"response data:{response.text}")
        try:
            data = json.loads(response.text)
            if data["msg"] == "OK" and not data["hasError"] and data["code"] == 200:
                # patch for qpython3
                cookies_file = os.path.join(
                    os.path.dirname(sys.argv[0]),
                    f".{self.config.mobile_no}.cookies",
                )
                self.browser.save_cookies(cookies_file)
                logging.info("登陆成功")
                return True
            else:
                logging.error(data["msg"])
                raise Exception()

        except Exception as e:
            logging.error(e)
            logging.error("登陆失败")
            sys.exit(-1)

    def select_doctor(self):
        """选择合适的大夫"""
        hospital_id = self.config.hospital_id
        department_id = self.config.department_id
        duty_code = self.config.duty_code
        duty_date = self.config.date

        # log current date
        logging.debug(f"当前挂号日期: {self.config.date}")

        payload = {
            'hospitalId': hospital_id,
            'departmentId': department_id,
            'dutyCode': duty_code,
            'dutyDate': duty_date,
            'isAjax': True
        }

        response = self.browser.post(self.get_doctor_url, data=payload)
        logging.debug(f"response data:{response.text}")

        try:
            data = json.loads(response.text)
            if data["msg"] == "OK" and not data["hasError"] and data["code"] == 200:
                self.dutys = data["data"]

        except Exception as e:
            logging.error(repr(e))
            sys.exit()

        if len(self.dutys) == 0:
            return "NotReady"

        self.print_doctor()

        for doctor in self.dutys[::-1]:
            if doctor["doctorName"] == self.config.doctorName and doctor['remainAvailableNumber']:
                logging.info("选中:" + str(doctor["doctorName"]))
                return doctor
        for doctor in self.dutys[::-1]:
            if doctor['remainAvailableNumber']:
                logging.info("选中:" + str(doctor["doctorName"]))
                return doctor
        return "NoDuty"

    def print_doctor(self):

        logging.info("当前号余量:")
        x = PrettyTable()
        x.border = True
        x.field_names = ["医生姓名", "擅长", "号余量"]
        for doctor in self.dutys:
            x.add_row([doctor["doctorName"], doctor['skill'], doctor['remainAvailableNumber']])
        print(x.get_string())

    def get_it(self, doctor, sms_code):
        """
        挂号
        """
        duty_source_id = str(doctor['dutySourceId'])
        hospital_id = self.config.hospital_id
        department_id = self.config.department_id
        patient_id = self.config.patient_id
        doctor_id = str(doctor['doctorId'])

        payload = {
            'dutySourceId': duty_source_id,
            'hospitalId': hospital_id,
            'departmentId': department_id,
            'doctorId': doctor_id,
            'patientId': patient_id,
            'hospitalCardId': "",
            'medicareCardId': "",
            "reimbursementType": "10",          # 报销类型
            'smsVerifyCode': sms_code,          # TODO 获取验证码
            'childrenBirthday': "",
            'isAjax': True
        }
        response = self.browser.post(self.confirm_url, data=payload)
        logging.debug(f"response data:{response.text}")

        try:
            data = json.loads(response.text)
            if data["msg"] == "OK" and not data["hasError"] and data["code"] == 200:
                logging.info("挂号成功")
                return True
            else:
                logging.error(data["msg"])
                return False

        except Exception as e:
            logging.error(repr(e))
            time.sleep(1)

    def gen_doctor_url(self, doctor):

        return self.patient_id_url + str(self.config.hospital_id) + \
           "-" + str(self.config.department_id) + "-" + str(doctor['doctorId']) + "-" +   \
            str(doctor['dutySourceId']) + ".htm"

    def get_patient_id(self, doctor):

        """获取就诊人Id"""
        if isinstance(doctor, str):
            #logging.error("没号了,  亲~")
            #sys.exit(-1)
            return # 无号退出逻辑由上级函数run()负责
        addr = self.gen_doctor_url(doctor)
        response = self.browser.get(addr, "")
        ret = response.text
        m = re.search(u'<input type=\\"radio\\" name=\\"hzr\\" value=\\"(?P<patientId>\d+)\\"[^>]*> ' + self.config.patient_name, ret)
        if m is None:
            sys.exit("获取患者id失败")
        else:
            self.config.patient_id = m['patientId']
            logging.info(f"病人ID:{self.config.patient_id}")

            return self.config.patient_id

    def gen_department_url(self):
        return self.department_url + str(self.config.hospital_id) + \
            "-" + str(self.config.department_id) + ".htm"

    def get_duty_time(self):
        """获取放号时间"""
        addr = self.gen_department_url()
        response = self.browser.get(addr, "")
        ret = response.text

        # 放号时间
        m = re.search('<span>更新时间：</span>每日(?P<refreshTime>\d{1,2}:\d{2})更新', ret)
        refresh_time = m['refreshTime']
        # 放号日期
        m = re.search('<span>预约周期：</span>(?P<appointDay>\d+)<script.*', ret)
        appoint_day = m['appointDay']

        today = datetime.date.today()

        # 优先确认最新可挂号日期
        self.stop_date = today + datetime.timedelta(days=int(appoint_day))
        logging.info("今日可挂号到: " + self.stop_date.strftime("%Y-%m-%d"))

        # 自动挂最新一天的号
        if self.config.date == 'latest':
            self.config.date = self.stop_date.strftime("%Y-%m-%d")
            logging.info(f"当前挂号日期变更为: {self.config.date}")

        # 生成放号时间和程序开始时间
        con_data_str = f"{self.config.date} {refresh_time}:00"
        self.start_time = datetime.datetime.strptime(con_data_str, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(days= - int(appoint_day))
        logging.info("放号时间: " + self.start_time.strftime("%Y-%m-%d %H:%M"))

    def get_sms_verify_code(self):
        """获取短信验证码"""
        response = self.browser.post(self.send_code_url, "")
        data = json.loads(response.text)
        logging.debug(response.text)
        if data["msg"] == "OK." and data["code"] == 200:
            logging.info("获取验证码成功")
            if self.imessage is not None: # 如果使用 iMessage
                return self.imessage.get_verify_code()
            elif self.qpython3 is not None: # 如果使用 QPython3
                return self.qpython3.get_verify_code()
            else:
                return input("输入短信验证码: ")
        elif data["msg"] == "短信发送太频繁" and data["code"] == 812:
            logging.error(data["msg"])
            sys.exit()
        else:
            logging.error(data["msg"])
            return None

    def lazy(self):
        cur_time = datetime.datetime.now() + datetime.timedelta(seconds=int(time.timezone + 8*60*60))
        if self.start_time > cur_time:
            seconds = (self.start_time - cur_time).total_seconds()
            logging.info(f"距离放号时间还有{str(seconds)}秒")
            sleep_time = seconds - 60
            if sleep_time > 0:
                logging.info(f"程序休眠{str(sleep_time)}秒后开始运行")
                time.sleep(sleep_time)
                # 自动重新登录
                self.auth_login()

    def run(self):
        """主逻辑"""
        self.get_duty_time()
        self.auth_login()                       # 1. 登陆
        self.lazy()
        doctor = ""
        while True:
            doctor = self.select_doctor()       # 2. 选择医生
            self.get_patient_id(doctor)         # 3. 获取病人id
            if doctor == "NoDuty":
                # 如果当前时间 > 放号时间 + 30s
                if self.start_time + datetime.timedelta(seconds=30) < datetime.datetime.now():
                    # 确认无号，终止程序
                    logging.error("没号了,  亲~")
                    break
                else:
                    # 未到时间，强制重试
                    logging.debug("放号时间: " + self.start_time.strftime("%Y-%m-%d %H:%M"))
                    logging.debug("当前时间: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    logging.info("没号了,但截止时间未到，重试中")
                    time.sleep(1)
            elif doctor == "NotReady":
                logging.info("好像还没放号？重试中")
                time.sleep(1)
            else:
                sms_code = self.get_sms_verify_code()               # 获取验证码
                if sms_code is None:
                    time.sleep(1)

                result = self.get_it(doctor, sms_code)              # 4.挂号
                if result:
                    break                                           # 挂号成功


if __name__ == "__main__":

    if (len(sys.argv) == 3) and (sys.argv[1] == '-c') and (isinstance(sys.argv[2], str)):
        config_path = sys.argv[2]
        guahao = Guahao(config_path)
    else:
        guahao = Guahao()
    guahao.run()
