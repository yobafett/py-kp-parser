from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import os
import re

def writePageToFile(driver):
    timestr = time.strftime("%Y%m%d-%H%M%S")
    with open(timestr + ".html", "w", encoding="utf-8") as file:
        file.write(str(driver.page_source))

def writeStringToTxt(data, filename = None):
    if not filename:
        filename = time.strftime("%Y%m%d-%H%M%S")

    with open(str(filename) + ".txt", "a", encoding="utf-8") as file:
        file.write(data)   

def getCsvHeader():
    return 'n;id;title;originalTitle;kpScore;imdbScore;url;posterUrl;year;genre;country;director;time\n'

def getStringFromList(dataList):
    resultString = ''
    for elem in dataList:
        resultString += str(elem) + ', '
    return resultString[:-2]

def writeDictToCsv(data, filename = None):
    if not filename:
        filename = time.strftime("%Y%m%d-%H%M%S")

    if not os.path.exists(str(filename) + ".csv"):
        with open(str(filename) + ".csv", "w", encoding="utf-8") as file:
            file.write(getCsvHeader())
    
    with open(str(filename) + ".csv", "a", encoding="utf-8") as file:
        for dictionary in data:
            file.write(
                str(dictionary['n']) + ';' +
                str(dictionary['id']) + ';' +
                str(dictionary['title']) + ';' +
                str(dictionary['originalTitle']) + ';' +
                str(dictionary['kpScore']) + ';' +
                str(dictionary['imdbScore']) + ';' +
                str(dictionary['url']) + ';' +
                str(dictionary['posterUrl']) + ';' +
                str(getStringFromList(dictionary['info']['year'])) + ';' +
                str(getStringFromList(dictionary['info']['genre'])) + ';' +
                str(getStringFromList(dictionary['info']['country'])) + ';' +
                str(getStringFromList(dictionary['info']['director'])) + ';' +
                str(dictionary['info']['time']) + ';\n'
           )   

class KpParser:
    __baseMovieUrl = 'https://www.kinopoisk.ru/film/'
    __startId = 298
    __currentId = __startId
    __bs = None
    
    def __init__(self, headless = False):
        self.__driver = self.initDriver(headless)

    def __del__(self):
        try:
            if self.__driver:
                self.__driver.quit()
        except Exception:
            print(self.__driver)

    def initDriver(self, headless = False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('headless')
        chrome_options.add_argument("incognito")
        chrome_options.add_argument("log-level=3")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("disable-extensions")
        chrome_options.add_experimental_option("detach", True)

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(800, 600)

        driver.delete_all_cookies()

        return driver

    def capchaCheck(self):
        capchaSpan = self.__bs.find('span', {'class': ['Text','Text_weight_medium','Text_typography_headline-s']})
        if capchaSpan:
            if capchaSpan.text == 'Подтвердите, что запросы отправляли вы, а не робот':
                print('Capcha on ' + str(self.__currentId - self.__startId) + ' itteration')
                checkbox = self.__driver.find_element(By.ID, 'js-button')
                if checkbox:
                    time.sleep(0.5)
                    checkbox.click()
                    
                    title = self.refreshCapcha(5)
                    while title.text == 'Ой, Капча!':
                        print('You need to solve capcha manualy!')
                        title = self.refreshCapcha(5)
                else:
                    raise Exception('Cannot find capcha checkbox')

    def notFoundCheck(self):
        notFoundH1 = self.__bs.find('h1')
        if notFoundH1:
            if notFoundH1.text == '404. Страница не найдена':
                return True
        return False

    def getMovieTitle(self):
        movieTitleSpan = self.__bs.find('span', 'span.data-bin' == 'True')
        if movieTitleSpan:
            titleText = movieTitleSpan.text
            pattern = re.compile(r'\(\d+\)')
            resultText = pattern.sub('', titleText)
            return resultText.strip()
        else:
            print('movieTitleSpan - not found on id: ' + str(self.__currentId))
            return None

    def getMovieOriginalTitle(self):
        originalTitleSpan = self.__bs.find('span', {'class': ['styles_originalTitle__JaNKM']})
        if originalTitleSpan:
            return originalTitleSpan.text
        else:
            print('originalTitleSpan - not found on id: ' + str(self.__currentId))
            return None

    def getMovieKpScore(self):
        kpRateSpan = self.__bs.find('span', {'class': ['film-rating-value', 'styles_root__iV6le']})
        if kpRateSpan:
            kpScoreSpan = kpRateSpan.find('span')
            if kpScoreSpan:
                return kpScoreSpan.text + '0'
            else:
                print('kpScoreSpan - not found on id: ' + str(self.__currentId))
                return None
        else:
            print('kpRateSpan - not found on id: ' + str(self.__currentId))
            return None

    def getMovieImdbScore(self):
        imdbScoreSpan = self.__bs.find('span', {'class': ['styles_valueSection__0Tcsy']})
        if imdbScoreSpan:
            imdbScoreText = imdbScoreSpan.text
            pattern = re.compile(r'IMDb:\s+')
            resultText = pattern.sub('', imdbScoreText)
            return resultText.strip()
        else:
            print('imdbScoreSpan - not found on id: ' + str(self.__currentId))
            return None

    def checkMovieTitle(self):
        movieTitleSpan = self.__bs.find('span', 'span.data-bin' == 'True')
        while not movieTitleSpan:
            time.sleep(0.5)
            self.updateParseContent()
            movieTitleSpan = self.__bs.find('span', 'span.data-bin' == 'True')

    def getInfoBlock(self, div):
        resultList = []
        aLinks = div.findAll('a', {'class': ['styles_linkDark__7m929', 'styles_link__3QfAk']})
        if aLinks:
            for a in aLinks:
                if 'слова' not in a.text and '...' not in a.text:
                    resultList += [a.text]
        return resultList

    def getMinutesFromTimeString(self, timeDiv):
        timeText = timeDiv.text
        pattern = re.compile(r'\s*мин\.\s*/\s*\d{2}:\d{2}\s*')
        resultText = pattern.sub('', timeText)
        return resultText.strip()

    def getMovieInfo(self):
        infoDivs = self.__bs.findAll('div', {'class': ['styles_rowDark__ucbcz', 'styles_row__da_RK']})
        if infoDivs:
            for div in infoDivs:
                infoDivTitle = div.find('div', {'class': ['styles_titleDark___tfMR', 'styles_title__b1HVo']})
                if infoDivTitle:
                    match infoDivTitle.text:
                        case 'Год производства':
                            year = self.getInfoBlock(div)
                        case 'Жанр':
                            genre = self.getInfoBlock(div)
                        case 'Страна':
                            country = self.getInfoBlock(div)
                        case 'Режиссер':
                            director = self.getInfoBlock(div)
                        case 'Время':
                            timeDiv = div.find('div', {'class': ['styles_valueDark__BCk93', 'styles_value__g6yP4']})
                            if timeDiv:
                                time = self.getMinutesFromTimeString(timeDiv)
        return {
            'year': year if year else '',
            'genre': genre if genre else '',
            'country': country if country else '',
            'director': director if director else '',
            'time': time if time else ''
        }

    def updateParseContent(self):
        page = self.__driver.page_source
        self.__bs = BeautifulSoup(page,'lxml')

    def refreshCapcha(self, delay):
        time.sleep(delay)
        self.updateParseContent()
        return self.__bs.find('title')

    def getParsedData(self, quantity, startsAt = 0):
        resultList = []
        self.__currentId = self.__startId + startsAt
        
        while self.__currentId <= self.__startId + quantity + startsAt:
            url = self.__baseMovieUrl + str(self.__currentId)
            self.__driver.get(url)
            self.updateParseContent() 
            self.capchaCheck()           

            if self.notFoundCheck():
                print('Not found id: '+ str(self.__currentId))
                time.sleep(1.5)
            else:
                self.checkMovieTitle()

                title = self.getMovieTitle()
                originalTitle = self.getMovieOriginalTitle()
                kpScore = self.getMovieKpScore()
                imdbScore = self.getMovieImdbScore()
                info = self.getMovieInfo()
                
                resultList.append({
                    'n': self.__currentId - self.__startId + 1,
                    'id': self.__currentId,
                    'title': title if title else '',
                    'originalTitle': originalTitle if originalTitle else '',
                    'kpScore': kpScore if kpScore else '',
                    'imdbScore': imdbScore if imdbScore else '',
                    'url': url,
                    'posterUrl': 'http://st.kinopoisk.ru/images/film_big/' + str(self.__currentId) + '.jpg',
                    'info': info
                })
            self.__currentId += 1
        return resultList

parser = KpParser()
data = parser.getParsedData(50, 42)
writeDictToCsv(data, 'dump')
