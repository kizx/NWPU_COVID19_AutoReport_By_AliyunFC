import requests
import re
from bs4 import BeautifulSoup
import location
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
import datetime
import pytz
import logging
import json

logging.basicConfig(level=logging.INFO)

# 全局变量
url_Form = "http://yqtb.nwpu.edu.cn/wx/ry/jrsb.jsp"  # 获取表格并进行操作
url_Submit = "http://yqtb.nwpu.edu.cn/wx/ry/ry_util.jsp"  # 用于 POST 申报的内容
url_for_id = "https://uis.nwpu.edu.cn/cas/login"  # 用于 Validate 登录状态
url_for_user_info = "http://yqtb.nwpu.edu.cn/wx/ry/jbxx_v.jsp"  # 「个人信息」一栏
url_for_list = "http://yqtb.nwpu.edu.cn/wx/xg/yz-mobile/rzxx_list.jsp"
url_for_yqtb_logon = "http://yqtb.nwpu.edu.cn//sso/login.jsp"


def login(username, password, session):
    header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/83.0.4103.116 Safari/537.36 "
    }
    data = {
        "username": username,
        "password": password,
        "_eventId": "submit",
        "currentMenu": "1",
        "execution": "e1s1",
    }
    header_get = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.26 Safari/537.36"
    }
    session.get(url_for_id, headers=header_get)
    session.headers.update(header)
    rt = session.post(
        url_for_id, data=data, headers=header, timeout=5
    ).text  # rt 以 html 形式返回登录状态
    if rt.find("欢迎使用") != -1:
        logging.info("登录成功！")
    else:
        logging.info("登录失败！请检查「登录信息」一栏用户名及密码是否正确")
        return {"code": 1, "msg": "登录失败！请检查户名及密码是否正确"}
    # r2、r3 用于动态获取相关信息填入 Form // for POST
    # r2 操作
    r2 = session.post(url_Form)  # 伪造一次对 Form 页面的请求，获得 JSESSIONID
    header3 = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.26 Safari/537.36",
        "Host": "yqtb.nwpu.edu.cn",
        "cookie": "JSESSIONID=" + str((session.cookies.values()[2])),
    }
    data2 = {
        "ticket": str((session.cookies.values()[1])),
        "targetUrl": "base64aHR0cDovL3lxdGIubndwdS5lZHUuY24vL3d4L3hnL3l6LW1vYmlsZS9pbmRleC5qc3A=",
    }

    # 登录后跳转到主页 [//yqtb.nwpu.edu.cn/wx/xg/yz-mobile/index.jsp]；r2 最终可以获取姓名和学院
    r_log_on_yqtb2 = session.post(url_for_yqtb_logon, data=data2, headers=header3)

    global RealCollege, RealName, PhoneNumber

    # r3 操作
    r3 = session.post(url_for_user_info, data=data2, headers=header3).text
    soup2 = BeautifulSoup(r3, "html.parser")

    m = soup2.find_all("span")

    RealCollege = m[2].string
    RealName = m[1].string
    PhoneNumber = m[6].string  # 提取出列表的 #6 值即为电话号码

    # print(RealCollege, RealName, PhoneNumber)

    # r5 操作：获得上一次填报的所在地
    r5 = session.post(url_for_list, data=data2, headers=header3).text
    soup3 = BeautifulSoup(r5, "html.parser")
    v_loc = soup3.find("span", attrs={"class": "status"}).string
    global loc_name, loc_code_str
    loc_name = v_loc
    loc_code = location.GetLocation(loc_name)
    if loc_name == "在西安":
        loc_code_str = "2"
    elif loc_name == "在学校":
        loc_code_str = "1"
    else:
        loc_code_str = loc_code[0]
    if loc_code_str == "" and loc_name != "在西安" and loc_name != "在学校":
        logging.error("获取上一次填报的信息时出现错误！")
        return "获取上一次填报的信息时出现错误！"
    return {"code": 0, "msg": "登录成功"}


def submit(
    loc_code_str, loc_name, RealName, RealCollege, PhoneNumber, username, session
):
    header3 = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4204.0",
        "Host": "yqtb.nwpu.edu.cn",
        "cookie": "JSESSIONID=" + str((session.cookies.values()[2])),
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "upgrade-insecure-requests": "1",
        "cache-control": "no-cache",
    }
    data2 = {
        "ticket": str((session.cookies.values()[1])),
        "targetUrl": "base64aHR0cDovL3lxdGIubndwdS5lZHUuY24vL3d4L3hnL3l6LW1vYmlsZS9pbmRleC5qc3A=",
    }
    html = session.get(url=url_Form, data=data2, headers=header3).text
    url = re.findall(r"url:'(ry_ut.*?)'", html)[0]
    hsjc = re.search("近48小时内是否进行过核酸检测？", html)
    hsjc = "1" if hsjc else "0"
    HeadersForm = {
        "Host": "yqtb.nwpu.edu.cn",
        "Origin": "http://yqtb.nwpu.edu.cn",
        "Referer": "http://yqtb.nwpu.edu.cn/wx/ry/jrsb.jsp",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Cookie": "JSESSIONID=" + str((session.cookies.values()[2])),
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.26 Safari/537.36",
        "Referer": "http://yqtb.nwpu.edu.cn/wx/ry/jrsb.jsp",
        "Origin": "http://yqtb.nwpu.edu.cn",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    tbDataForm = {
        "hsjc": hsjc,  # 核酸检测
        "xasymt": "1",  # 西安市一码通
        "bdzt": "1",
        # "sfczbcqca": "",
        # "czbcqcasjd": "",
        # "sfczbcfhyy": "",
        # "czbcfhyysjd": "",
        "actionType": "addRbxx",
        "userLoginId": username,
        # "fxzt": "9",
        "userType": "2",
        "userName": RealName,  # 真实姓名；实践表明可留空，以防万一填上，下同
        "szcsbm": loc_code_str,  # 所在城市编码
        "szcsmc": str(loc_name),  # 所在城市名称
        # "sfjt": "0",  # 是否经停
        # "sfjtsm": "",  # 是否经停说明
        # "sfjcry": "0",  # 是否接触人员
        # "sfjcrysm": "",  # 说明
        # "sfjcqz": "0",  # 是否接触确诊
        "sfyzz": "0",  # 是否有症状
        "sfqz": "0",  # 是否确诊
        "ycqksm": "",
        # "glqk": "0",  # 隔离情况
        # "glksrq": "",  # 隔离开始日期
        # "gljsrq": "",  # 隔离结束日期
        "tbly": "sso",  # 填报来源：SSO 单点登录
        # "glyy": "",  # 隔离原因
        "qtqksm": "",  # 其他情况说明
        # "sfjcqzsm": "",
        # "sfjkqk": "0",
        # "jkqksm": "",  # 健康情况说明
        # "sfmtbg": "",
        # "qrlxzt": "",
        # "xymc": RealCollege,  # 学院名称；实践表明可留空
        # "xssjhm": PhoneNumber,  # 手机号码；实践表明可留空
        # "xysymt": "1",  # 西安市一码通：绿码
    }

    r4 = session.post(
        url=f"http://yqtb.nwpu.edu.cn/wx/ry/{url}",
        data=tbDataForm,
        headers=HeadersForm,
    )
    state = r4.json()
    session.close()

    if (state["state"]) == "1":
        logging.info("申报成功！")
        msg = f"""姓名：{tbDataForm['userName']}
48小时核酸：{'是' if hsjc=='1' else '否'}
当前位置：{tbDataForm['szcsmc']}
申报时间：{datetime.datetime.now(pytz.timezone("PRC")).strftime("%m-%d %a %H:%M:%S")}
"""
        return {"code": 0, "msg": msg}
    else:
        logging.error("申报失败，请重试！")
        return {"code": 1, "msg": "申报失败，请重试！"}


def push(event, code, msg):
    if (code or event.get("wecompush", False)) and event.get("userid", False):
        body = {
            "sendkey": "kizxmoe",
            "msg_type": "text",
            "msg": msg,
            "to_user": event["userid"],
        }
        requests.post(
            "https://service-o5la6lv0-1259445933.hk.apigw.tencentcs.com/release/wecomchan",
            json=body,
        )
        logging.info("wocom推送成功！")

    if event.get("serverpush", False) and event.get("api", False):
        try:
            url = f"https://sctapi.ftqq.com/{event['api']}.send"
            text = {"title": "疫情填报通知", "desp": msg}
            requests.post(url, data=text)
            logging.info("server酱推送成功！")
        except Exception as e:
            logging.error("server酱推送失败！")
    if (code or event["emailpush"]) and event["email"]:
        try:
            message = MIMEText(msg, "plain", "utf-8")  # 内容, 格式, 编码
            message["From"] = formataddr(["疫情填报通知", "yqtb@nwpu.email"])
            message["To"] = event["email"]
            message["Subject"] = msg
            smtpObj = smtplib.SMTP_SSL("smtp.ym.163.com", 994)  # 启用SSL发信, 端口一般是465
            smtpObj.login("yqtb@nwpu.email", "27XXSdlgGB")  # 登录验证
            smtpObj.sendmail(
                "yqtb@nwpu.email", event["email"], message.as_string()
            )  # 发送
            logging.info("邮件发送成功！")
        except Exception as e:
            logging.error("邮件发送失败！")
    if code and event["phonenumber"]:
        logging.info("短信发送。。。")


def main(event):
    logging.info(f"{event['name']}开始填报!")
    session = requests.Session()
    session.get(url_for_id)  # 从 CAS 登录页作为登录过程起点
    logres = login(event["username"], event["password"], session)
    res = logres
    if not res["code"]:
        res = submit(
            loc_code_str,
            loc_name,
            RealName,
            RealCollege,
            PhoneNumber,
            event["username"],
            session,
        )
    push(event, res["code"], res["msg"])
    return res


if __name__ == "__main__":
    msg = main(
        {
            "name": "昵称，可任意填",
            "username": "学号",
            "password": "翱翔门户密码",
            "serverpush": True,
            "api": "server酱的api",
            "phonenumber": "手机号，目前没有用",
            "emailpush": True,
            "email": "推送消息邮箱",
            "wecompush": True,
            "userid": "企业微信的用户id",
        }
    )
    print(msg)
