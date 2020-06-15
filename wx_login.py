import asyncio
import random
import re
import json
import grequests
from PIL import Image
from pyppeteer.launcher import launch



class WxGzhSpider(object):
    def __init__(self, fingerprint_dict):
        self.token = fingerprint_dict['token'][0]
        self.headers = {
            'cookie': fingerprint_dict['cookies'],
            'Connection': 'keep-alive',
            'Host': 'mp.weixin.qq.com',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }

    def gzh_base(self, gzh_name_query):
        """
        提取公众号信息
        :param gzh_name_query:
        :return:
        """
        # for base_query in gzh_name_query:
        base_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz?action=search_biz&begin=0&count=5&query={}&token={}&lang=zh_CN&f=json&ajax=1'
        # 抓取公众号信息
        base_req_list = [grequests.get(base_url.format(gzh_id, self.token), headers=self.headers, verify=False) for gzh_id in gzh_name_query]
        base_resp_list = grequests.map(base_req_list)
        base_resp_body_list = [base_resp.json() for base_resp in base_resp_list]
        # 提取出的格式示例 [{'fakeid': 'MjM5MTY0Njg0MA==', 'nickname': '北大清华讲座', 'alias': 'bdqhjz'}]
        gzh_nickname = [{'fakeid': base['fakeid'], 'nickname': base['nickname'], 'alias': base['alias'], } for i in
                        base_resp_body_list for base in i['list']]
        return gzh_nickname

    def gzh_app_page(self, gzh_nickname):
        """
        获取公众号文章page信息
        :param gzh_nickname:
        :return:
        """
        app_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&begin=0&count=5&fakeid={}&type=9&query=&token={}&lang=zh_CN&f=json&ajax=1'
        app_req_list = [grequests.get(app_url.format(i['fakeid'], self.token), headers=self.headers, verify=False) for i in gzh_nickname]
        app_resp_list = grequests.map(app_req_list)
        # 获取公众号文章page
        app_resp_body_first = [base_resp.json() for base_resp in app_resp_list]

        page = int((int(app_resp_body_first[0]['app_msg_cnt']) / 5)) + 1
        return page

    def gzh_all_app(self, gzh_nickname, page):
        app_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&begin={}&count=5&fakeid={}&type=9&query=&token={}&lang=zh_CN&f=json&ajax=1'
        data_dict = {}
        for alias in gzh_nickname:
            app_req_list = [grequests.get(app_url.format(j, alias['fakeid'], self.token), headers=self.headers, verify=False)
                                  # for i in gzh_nickname for j in range(int(page))]
                                  for j in range(int(3))]
            app_resp_list = grequests.map(app_req_list)
            app_resp_body_list = [base_resp.json() for base_resp in app_resp_list]

            # 清洗数据
            data_dict[alias['alias']] = {}
            data_dict[alias['alias']]['befrom'] = {
                'nickname': alias['nickname'],
                'alias': alias['alias']
            }
            data_dict[alias['alias']]['data'] = []
            for app_data in app_resp_body_list:
                for article_data in app_data['app_msg_list']:
                    dic = {}
                    dic['digest'] = article_data['digest']
                    dic['title'] = article_data['title']
                    dic['link'] = article_data['link']
                    data_dict[alias['alias']]['data'].append(dic)
        return data_dict, 'OK'




async def main(username, password, gzh_name_query):
    """
    基于pyppeteer登录微信公众号平台
    :param username:
    :param password:
    :return:
    """
    # 启动pyppeteer
    browser = await launch({'headless': False, 'args': ['--no-sandbox'], })
    # 启动个新的浏览器页面
    page = await browser.newPage()
    await page.setUserAgent(
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36')
    await page.goto('https://mp.weixin.qq.com/')  # 访问https://mp.weixin.qq.com/页面
    # 替换微信在检测浏览时一些参数。
    # 就是在浏览器运行的时候，始终让window.navigator.webdriver=false
    # navigator是windiw对象的一个属性，同时修改plugins，languages，navigator 且让
    await page.evaluate(
        '''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => false } }) }''')  # 以下为插入中间js，将微信会为了检测浏览器而调用的js修改其结果。
    await page.evaluate('''() =>{ window.navigator.chrome = { runtime: {},  }; }''')
    await page.evaluate('''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''')
    await page.evaluate('''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }''')
    await page.click("#header > div.banner > div > div > div.login__type__container.login__type__container__scan > a")
    # 设置username,password输入框输入规则
    input_time_random = random.randint(100, 151)
    await page.type(
        "#header > div.banner > div > div > div.login__type__container.login__type__container__account > form > div.login_input_panel > div:nth-child(1) > div > span > input",
        username, {'delay': input_time_random - 50})
    await page.type(
        "#header > div.banner > div > div > div.login__type__container.login__type__container__account > form > div.login_input_panel > div:nth-child(2) > div > span > input",
        password, {'delay': input_time_random})
    # 输入完成等待0.5秒之后点击登录
    await page.waitFor(0.5 * 1000)
    await page.click(
        "#header > div.banner > div > div > div.login__type__container.login__type__container__account > form > div.login_btn_panel > a")  # 点击登录按钮
    # 点击登录之后等待页面加载微信二维码
    await page.waitFor(2 * 1000)
    # 获取微信二维码截图并展示在本地
    # 扫描登录微信二维码
    yazhengma = await page.waitForSelector(
        '#app > div.weui-desktop-layout__main__bd > div > div.js_scan.weui-desktop-qrcheck > div.weui-desktop-qrcheck__qrcode-area > div > img')  # 通过css selector定位验证码元素
    await yazhengma.screenshot({'path': 'yazhengma.png'})  # 注意这里用的是ele.screenshot方法与教程1 page.screenshot是不同的
    base = Image.open('yazhengma.png')
    base.show()
    print('请扫描微信二维码确认登陆')
    # 如果扫描确认之后请输入 y 告诉程序确认登录
    affirm_id = input('请输入确认或者未确认(y/n)')
    fingerprint_dict = {}
    if affirm_id == 'y':
        # 获取登录cookies
        print('登录成功正在获取cookies')
        cookies_list = await page.cookies()
        print(cookies_list)
        cookies = await get_cookies(page)
        print('获取cookies成功')
        fingerprint_dict['cookies'] = cookies
        # 获取登录token
        after_landing_url = page.url
        token = re.findall(r'token=(\d+)', after_landing_url)
        fingerprint_dict['token'] = token
        print(fingerprint_dict)

        # 调用爬虫模块
        wxgzhspider = WxGzhSpider(fingerprint_dict)
        gzh_nickname = wxgzhspider.gzh_base(gzh_name_query)
        page = wxgzhspider.gzh_app_page(gzh_nickname)
        data_dict,msg_code = wxgzhspider.gzh_all_app(gzh_nickname, page)
        with open('data.js', 'w', encoding='utf-8') as file:
            json.dump(data_dict, file, ensure_ascii=False)
        if msg_code == "OK":
            await page.close()
            return 'success'
        else:
            print('IP封锁...')
            await page.close()
            return 'fail'


    else:
        print('登录失败, 正在重新登录...')
        await page.close()
        return 'fail'


async def get_cookies(page):
    """
    提取cookies
    :param page:
    :return:
    """
    cookies_list = await page.cookies()
    cookies = ''
    for cookie in cookies_list:
        if cookie == cookies_list[-1]:
            str_cookie = '{0}={1};'
        else:
            str_cookie = '{0}={1}; '
        str_cookie = str_cookie.format(cookie.get('name'), cookie.get('value'))
        cookies += str_cookie
    return cookies


if __name__ == '__main__':
    username = '2831886066@qq.com'
    password = '422gices'
    gzh_name_query = ['csdn_code']
    while 1:
        cookies = asyncio.get_event_loop().run_until_complete(main(username, password, gzh_name_query))
        print('***************************************************************')
        print(cookies)
        if cookies == 'fail':
            print('正在重新启动登录程序...')
        else:
            print('程序结束')
