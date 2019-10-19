import numpy as np
import cv2 as cv
import math as mh
import time as ti
import random as rm
import copy

# region Глобальные переменные
wname = 'Body and photons'  # Название окна
shipsize = 4                
shcnt = 3                   
fcnt = 200                  # Количество фотонов в пучке
fv = 30                     # Скорость фотонов
bvel = 10                   # Скорость кораблей
fr = 1                      # Радиус фотонов
wth = 2*1280                # Ширина окна
lth = 2*720                 # Высота
x0 = int(wth/2)             # Начало координат
y0 = int(lth/2)             #
# endregion

# region Функции физики

# Cоздание пучка фотонов
def createBunch(x, y, fmass):                       
    fmass.append([[0,0,0] for c in range(fcnt)])    # добавляем следующий пучок в список пучков, пока присваиваем нули
    bunch = fmass[len(fmass)-1]                     # bunch это пучок который мы создаем
    for i in range(fcnt):                           # для каждого фонона из пучка...
        foton = bunch[i]                            # foton это фотон которому мы присваиваем начальные координаты
        foton[0] = x                                # присваиваем координаты из аргументов
        foton[1] = y                                #
        foton[2] = 2*3.14*(i/fcnt)                  # присваиваем угол, деля круг на равные части по количеству фотонов.

# функция возвращает угол между вектором с началом в точке (x, y) концом в точке (x1, y1) и вектором, направленным вдоль оси x
def setAngle(x,y,x1,y1):  
    # условие нужно, чтобы устранить неопределенность в знаке при вычислении из скалярного произведения 
    if (y1-y) < 0:  # если точка имеет большую, чем точка 1, координату по y, то есть на картинке она НИЖЕ
        return 2*mh.pi-mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) 
    else:           # если точка на картинке находится ВЫШЕ
        return mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2))))

# функция добавляет еще один корабль в shmass. присваивает ему заданные координаты, и если угол не задан, корабль летит в центр.
def createShip(shmass, x, y, afa = 10):             # функция для создания корабля, принимает массив кораблей, координаты, направление (опц.)
    if afa == 10:                                   # если афа не задана, то она принимает десятку как знак того, что корабль
        afa = setAngle(x,y,x0,y0)                   # должен лететь в точку x0, y0. 
    shmass.append([x,y,afa]) 

# функция даёт приращение координате каждого корабля вдоль его направления и создаёт в этой точке пучок фотонов.
def moveShip(shmass, fmass):
    for i in range(len(shmass)):
        ship = shmass[i]                                # ship это корабль которому мы даём приращение
        ship[0] = ship[0] + int(bvel*mh.cos(ship[2]))   # даём приращение вдоль x
        ship[1] = ship[1] + int(bvel*mh.sin(ship[2]))   # и вдоль y
        createBunch(ship[0],ship[1], fmass)             # создаем пучок фотонов в этой точке

# функция даёт приращение координате каждого фотона вдоль его направления.
def movePhot(fmass):
    for b in range (len(fmass)):                    # для каждого пучка...
        for f in range (len(fmass[b])):             # для каждого фотона из пучка...
            f_afa = fmass[b][f][2]                  # работаем с углом поворота фотона относительно горизонтальной оси, по часовой стрелке!
            fmass[b][f][0] += fv*mh.cos(f_afa)      # приращение координат фотона в направлении этого угла
            fmass[b][f][1] += fv*mh.sin(f_afa)      #
 # endregion

# region Функции графики

# функция рисует корабли, то есть кружки, центры кружков хранятся в shmass, радиус - в глобальной переменной shipsize
def drawShip(shmass, colour):       
    for i in range(len(shmass)):
        ship = shmass[i]
        cv.circle(img, (ship[0], ship[1]), shipsize, colour, -1)

# функция рисует фотоны, то есть кружки, центры кружков хранятся в fmass, радиус - в глобальной переменной fr
def drawPhot(fmass, colour):
    for b in range(len(fmass)):
        bunch = fmass[b]
        for f in range(len(bunch)):
            foton = bunch[f]
            cv.circle(img, (int(foton[0]), int(foton[1])), fr, colour, -1)
# endregion

# Обработка физики
def phys(fmass, shmass): #Обработка всей физики
    #Движение тела и испускание им фотонов
    moveShip(shmass, fmass)
    movePhot(fmass)

# Обработка графики
def graph(draw, img, fmass, shmass):    # draw: если 1, то закрашиваем, если 0 - то стираем, то есть рисуем черным
    # цвет закрашивания
    if draw == 1:
        colour, colour1 = (255,255,255), (0,255,255) #белый и желтый
    else:
        colour, colour1 = (0,0,0), (0,0,0) # черный (стираем)
    # просто кружок в центре
    cv.circle(img, (x0, y0), 60, colour, -1)

    drawShip(shmass, colour)
    drawPhot(fmass, colour1)

# Главная функция
def main():
    fmass = [[]]                        # создаём трёхмерный массив, хранящий все пучки, каждый пучок хранит все фотоны, фотоны - 
                                        # свои координаты и угол относительно направления оси x по часовой стрелке.
    shmass = []                         # массив кораблей, хранящий каждый корабль, корабль хранит свои координаты и угол.

    #для примера создаём три корабля, не задаём угол, чтобы они летели к центру
    createShip(shmass, 500, 300)
    createShip(shmass, 2000, 300)
    createShip(shmass, 1000, 300)

    for t in range(50): # выполняем программу в течение 50 итераций
        graph(0, img, fmass, shmass)    # стираем старое
        phys(fmass, shmass)             # изменяем координаты в соответствии со скоростями
        graph(1, img, fmass, shmass)    # рисуем новое
        cv.imshow(wname, img)           
        cv.waitKey(1)

cv.namedWindow(wname, cv.WINDOW_NORMAL) # создаём окно размером 1280 на 720
cv.resizeWindow(wname, 1280, 720)       #
img = np.zeros((lth, wth, 3))           # Массив для самой картинки, с кораблями и фотонами и установкой

main() 