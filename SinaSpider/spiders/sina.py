import scrapy
from scrapy.http import Request
import random
import json
import time
import csv

# FIXME Config Settings

UserAgent = [
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/600.8.9 (KHTML, like Gecko) Version/8.0.8 Safari/600.8.9',
    'Mozilla/5.0 (iPad; CPU OS 8_4_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12H321 Safari/600.1.4',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0'
]

def get_header():
    header = {
        'UserAgent' : UserAgent[random.randint(0,len(UserAgent) - 1)],
        'X-Requested-With': 'XMLHttpRequest',
        'X-Xsrf-Token': 'f0d097',
        'Connection':'close'
    }

    return header

# FIXME: Elegant exit

class SinaSpider(scrapy.Spider):
    name = "sina"
    allowed_domains = ["m.weibo.cn"]
    start_urls = ["https://m.weibo.cn/api/container/getIndex?t=0&luicode=10000011&lfid=100103type%3D1%26q%3Dsensetime&containerid=1076035477684004&since_id=4775625736848835"]
    output_csv = './output/output.csv'

    def start_requests(self):
        header = get_header()
        yield Request(url = self.start_urls[0],headers=header, callback=self.get_page)

    def get_page(self, response):
        page_content = json.loads(response.text)
        last_crawled_data = response.meta
        if 'blogs' in last_crawled_data:
            with open(self.output_csv, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for blog in last_crawled_data['blogs']:
                    data = [blog['content'], blog['time'], blog['id']]
                    if 'repost_from' in blog:
                        data.append(blog['repost_from'])
                        data.append(blog['repost_content'])
                    
                    writer.writerow(data)
                    
        since_id = page_content['data']['cardlistInfo']['since_id']
        meta = {'index' : 0, 'since_id':since_id, "blogs":[]}

        for blog in page_content['data']['cards']:
            blog_dict = {}
            blog_dict['content'] = ""
            blog_dict['id'] = blog['mblog']['id']
            blog_dict['time'] = blog['mblog']['created_at']
            
            if 'retweeted_status' in blog['mblog']:
                if blog['mblog']['retweeted_status']['user'] != None:
                    blog_dict['repost_from'] = blog['mblog']['retweeted_status']['user']['screen_name']
                else:
                    blog_dict['repost_from'] = 'null'
                blog_dict['repost_id'] = blog['mblog']['retweeted_status']['id']
                blog_dict['repost_content'] = ""

            meta['blogs'].append(blog_dict)

        blog_url = 'https://m.weibo.cn/statuses/extend?id=' + str(meta['blogs'][meta['index']]['id'])
        meta['index'] += 1
        time.sleep(3)
        yield Request(blog_url, headers=get_header(), callback=self.get_blog, meta=meta)

    def get_blog(self, response):
        blog_json = json.loads(response.text)
        if 'errno' in blog_json:
            blog_data = blog_json['msg']
        else:
            blog_data = blog_json['data']['longTextContent']

        meta = response.meta
        index = meta['index']
        
        meta['blogs'][index-1]['content'] = blog_data

        header= get_header()
        if 'repost_from' in meta['blogs'][index-1]:
            repost_blog_url = 'https://m.weibo.cn/statuses/extend?id=' + str(meta['blogs'][index-1]['repost_id'])
            time.sleep(3)
            yield Request(repost_blog_url, headers=header, callback=self.get_repost, meta=meta, dont_filter = True)
        else:
            if index == len(meta['blogs']):
                next_page = self.start_urls[0] + '&since_id=' + str(meta['since_id'])
                time.sleep(3)
                yield Request(next_page, headers=header, callback=self.get_page, meta=meta, dont_filter = True)
            else:
                next_blog = 'https://m.weibo.cn/statuses/extend?id=' + str(meta['blogs'][index]['id'])
                meta['index'] += 1
                time.sleep(3)
                yield Request(next_blog, headers=header, callback=self.get_blog, meta=meta, dont_filter = True)

    def get_repost(self, response):
        blog_json = json.loads(response.text)
        if 'errno' in blog_json:
            blog_data = blog_json['msg']
        else:
            blog_data = blog_json['data']['longTextContent']
        print(blog_data)
        print("-"*50)
        # FIXME: Nested repost
        meta = response.meta
        index = meta['index']
        meta['blogs'][index-1]['repost_content'] = blog_data
        header= get_header()
        if index == len(meta['blogs']):
            next_page = self.start_urls[0] + '&since_id=' + str(meta['since_id'])
            time.sleep(3)
            yield Request(next_page, headers=header, callback=self.get_page, meta=meta, dont_filter = True)
        else:
            next_blog = 'https://m.weibo.cn/statuses/extend?id=' + str(meta['blogs'][index]['id'])
            meta['index'] += 1
            time.sleep(3)
            yield Request(next_blog, headers=header, callback=self.get_blog, meta=meta, dont_filter = True)