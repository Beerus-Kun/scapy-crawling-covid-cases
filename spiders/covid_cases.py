import scrapy, re
from scrapy.http.response.text import TextResponse

# loại bỏ các chữ có dấu để thực hiện truy vấn
def no_accent_vietnamese(s):
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ]', 'A', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ÌÍỊỈĨ]', 'I', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ƯỪỨỰỬỮÙÚỤỦŨ]', 'U', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[ỲÝỴỶỸ]', 'Y', s)
    s = re.sub(r'[Đ]', 'D', s)
    s = re.sub(r'[đ]', 'd', s)

    marks_list = [u'\u0300', u'\u0301', u'\u0302', u'\u0303', u'\u0306',u'\u0309', u'\u0323']

    for mark in marks_list:
        s = s.replace(mark, '')
    return s

# Lọc title để lấy số lượng ca mới, theo mẫu
def new_case_amount(s):
    amounts = re.findall('THONG BAO VE ([0-9\.]+) CA MAC MOI', s)
    if len(amounts) == 0:
        return -1
    amount = re.sub('\.', '', amounts[0])
    return int(amount)


# Lọc nội dung để lấy số lượng và thành phố có ca mắc mới theo cấu trúc <tên thành phố> (<số lượng ca mới>)
def cases_in_cities( s):
    cities = re.findall('(tai|\,) ([^\(\)]+) \(([0-9\.]+)\)', s)
    city_arr = []

    for city in cities:
        city_arr.append({
            'city': city[1],
            'case': int(re.sub('\.', '', city[2]))
        })
    return city_arr

class CovidCasesSpider(scrapy.Spider):
    name = "covid_cases"
    allowed_domains = ["web.archive.org"]
    start_urls = ["https://web.archive.org/web/20210907023426/https://ncov.moh.gov.vn/vi/web/guest/dong-thoi-gian"]

    def parse(self, response:TextResponse):
        reports = response.xpath("//div[@class ='timeline']")
        for report in reports:
            # lấy dữ liệu thời gian
            time = report.xpath(".//div/div/h3/text()").get()

            # lấy dữ liệu title
            title = report.xpath(".//div/div/p[2]/text()").get()

            # lấy dữ liệu nội dung đoạn thứ 1 (thường lưu chi tiết về ca mắc mới ở thành phố)
            cities = report.xpath(".//div/div/p[3]/text()[1]").get()

            # kiểm tra nếu một phần tử None nghĩa là không theo cấu trúc mẫu
            if time is None or title is None or cities is None:
                continue
            
            # Lấy số lượng ca mắc mới
            amount = new_case_amount(no_accent_vietnamese(title))

            # Kiểm tra nếu -1 thì không phải bài viết về ca covid mới
            if amount == -1:
                continue

            yield {
                'time': time,
                "new_case" : amount,
                'city_case': cases_in_cities(no_accent_vietnamese(cities))
            }
            
        # lấy link trang tiếp theo, theo nút trang tiếp ở dưới    
        next_btn = response.xpath("//ul[@class='lfr-pagination-buttons pager']/li[2]")[0]
        next_link = next_btn.xpath(".//@href").get()
        next_class = next_btn.xpath(".//@class").get()

        # kiểm tra, nếu nút trang tiếp class = disabled thì nội đã được lưu lại hết
        if next_class.strip() == '':
            # lấy dữ liệu ở trang tiếp theo
            yield scrapy.Request(url=next_link, callback=self.parse)