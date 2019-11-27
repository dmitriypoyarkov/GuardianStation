import numpy as np
import cv2 as cv
import math as mh
import time as ti
import random as rm
import copy

# region Глобальные переменные
wname = 'Guardian Station'  # Название окна
shipsize = 4                # Количество кораблей (пока не использовалось)                   
fcnt = 500                  # Количество фотонов в пучке
fv = 50                     # Скорость фотонов
bvel = 10                   # Скорость кораблей
fr = 1                      # Радиус фотонов
wth = int(1*1280)           # Ширина окна (разрешение)
lth = int(1*720)            # Высота
x0 = int(wth/2)             # Центр карты, центр установки
y0 = int(lth/2)             # 
stR = 40                    # Радиус установки
pr = 1                      # Радиус точки из массива pmass
chet = True                 # Меняя эту переменную, сделаем испускание фотонов раз в два кадра.

#<A>
turretR = 22 #размер турели
bulletSpeed = 21#скорость снаряда
bulletR = 7# радиус снаряда
#</A>

# region <A>
class Turret():#класс турели
    def __init__(self, coordinates):#при создании новой турели задаём её координаты
        self.x, self.y = coordinates
    def draw(self, color):#рисуем турель
        cv.circle(img, (self.x,self.y), turretR, color, -1)
    def get_target_location(self, coordinates):
        #Получаем точку, в которую надо стрелять следующим образом: находим t, при котором r(t) - vt = min, где v - скорость снаряда,
        #при достаточном размере снаряда (или при большом массиве точек траектории), гарантированно попадаем
        tmin = 0
        range_min = 10000
        for t in range(len(coordinates)):
            if ((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - bulletSpeed * t < range_min:
                tmin = t
                range_min = ((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - bulletSpeed * t
        print(coordinates[tmin])
        return(coordinates[tmin])
    def fire(self, coordinates): #Стреляем по координатам корабля, возвращаем объект типа bullet
        return Bullet((self.x, self.y), self.get_target_location(coordinates))
  
class Bullet():
    def __init__(self, start, target):#инициализируем снаряд, задавая начальную точку и точку прилёта снаряда, находим проекцию скоростей
        r = ((start[0] - target[0]) ** 2 + (start[1] - target[1]) ** 2) ** 0.5
        self.x_speed = int((target[0] - start[0]) * bulletSpeed / r)
        self.y_speed = int((target[1] - start[1]) * bulletSpeed / r)
        self.x = start[0]
        self.y = start[1]
    def draw(self, color):#рисуем снаряд
        cv.circle(img, (self.x,self.y), bulletR, color, -1)
    def move(self):#сдвигаем снаряд, соответственно его времени
        self.x += self.x_speed
        self.y += self.y_speed
#endregion </A>

# region <Л>
# функция вычисляет линии, соответствующие направлениям фотонов, врезавшихся в установку
def calculate_b(pmass):
    abmass = []                                 # массив для линий на этом кадре
    for i in range(len(pmass)):                 # для каждой точки из pmass...
        if pmass[i][2] <= 2*mh.pi:              # если это точка с реальным углом, т. е. точка фотонов, а не кораблей
            if pmass[i][2] <= mh.pi:            # заносим коэффициенты прямой фотона в массив abmass, учитывая тупой угол
                a = mh.tan(pmass[i][2])         #
            else:                               #
                a = -mh.tan(mh.pi-pmass[i][2])  #
            b = pmass[i][1] - a*pmass[i][0]     #
            abmass.append([a, b, pmass[i][3]])  #четвертый параметр в abmass = номер корабля фотона
    return abmass                               #возвращает массив линий

#функция находит пересечения этих линий. для каждого корабля - свои линии и своя точка, номер корабля заносится в 4й параметр pmass.
def calculate_intersection(pmass, abmass):
    while len (abmass) > 0:                     # пока массив линий не опустошён
        a = abmass[0][0]                        # заносим для простоты нужные величины его 0-координаты
        b = abmass[0][1]                        #
        nbr = abmass[0][2]                      #
        i = 1                                   # счетчик для остальных прямых (наша - 0-я, начинаем с 1-й)
        ctr = 0                                 # счетчик тех прямых, с которыми мы учли пересечение
        coord = []                              # массив для двух координат, x y, с ним будем работать
        while i < len(abmass) and ctr <= 5:     # пока мы не дошли до конца и пока мы не усреднили координату с 5 соседями
            if nbr == abmass[i][2]:                             # если это прямые одного и того же корабля (в abmass это 3-й элемент)
                x = (abmass[i][1] - b)/(a - abmass[i][0])       # считаем их точку пересечения
                y = a*x + b                                     #
                if len(coord) != 0:                             # если это не первая точка пересечения в данном цикле
                    coord[0] = 0.5*(coord[0] + x)               # усредняем точку с уже имеющейся
                    coord[1] = 0.5*(coord[1] + y) 
                else:                                           # если первая, нужно сначала создать её
                    coord.append(x)                             #
                    coord.append(y)                             #
                abmass.pop(i)                                   # эту прямую мы учли, удаляем
                ctr += 1                                        # счетчик учтенных пересечений повышаем
                i -= 1                                          # так как мы удалили элемент, этот счетчик понижаем
            i += 1                                              # просто повышение счетчика цикла
        abmass.pop(0)                                           # нулевой элемент удаляем

        if (ctr >= 3):                                          # если учтено больше трёх пересечений (их не обязательно 5)
            pmass.append([coord[0], coord[1], 10, nbr])         # добавляем точку в pmass с номером корабля, испустившего фотон    
# endregion </Л>

# region Функции физики
# функция сообщает координаты столкновений фотонов с установкой
def photCollid(fmass, pmass):
    for b in range(len(fmass)):
        bunch = fmass[b]
        f = 0
        while f < len(bunch):
            foton = bunch[f]
            lx = int(foton[0]) - x0
            ly = int(foton[1]) - y0
            l = mh.sqrt(lx**2+ly**2)
            if l <= stR:
                pmass.append([ foton[0], foton[1], foton[2], foton[3] ]) 
                del bunch[f]
                f -= 1
            f += 1

# функция удаляет из массива точек все элементы, кроме тех, что с углом 10.
def clearPmass(pmass):
    i = 0
    while i < len(pmass):
        if not pmass[i][2] == 10:
            del pmass[i]
            i -= 1
        i += 1

# Cоздание пучка фотонов
def createBunch(x, y, fmass, nbr):                      
    fmass.append([[0,0,0,0] for c in range(fcnt)])  # добавляем следующий пучок в список пучков, пока присваиваем нули
    bunch = fmass[len(fmass)-1]                     # bunch это пучок который мы создаем
    for i in range(fcnt):                           # для каждого фонона из пучка...
        foton = bunch[i]                            # foton это фотон которому мы присваиваем начальные координаты
        foton[0] = x                              # присваиваем координаты из аргументов
        foton[1] = y
        foton[2] = 2*mh.pi*(i/fcnt)
        foton[3] = nbr                              #четвёртый параметр отвечает за корабль, от которого фотон отлетел
    

# функция возвращает угол между вектором с началом в точке (x, y) концом в точке (x1, y1) и вектором, направленным вдоль оси x
def setAngle(x,y,x1,y1):  
    # условие нужно, чтобы устранить неопределенность в знаке при вычислении из скалярного произведения 
    if (y1-y) < 0:  # если точка имеет большую, чем точка 1, координату по y, то есть на картинке она НИЖЕ
        return 2*mh.pi-mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) 
    else:           # если точка на картинке находится ВЫШЕ
        return mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2))))

# функция возвращает угол между вектором с началом в точке (x, y) концом в точке (x1, y1) и вектором, направленным вдоль оси x
# с разбросом в +/- 45 градусов
def setAngleRand(x,y,x1,y1):  
    # условие нужно, чтобы устранить неопределенность в знаке при вычислении из скалярного произведения 
    if (y1-y) < 0:  # если точка имеет большую, чем точка 1, координату по y, то есть на картинке она НИЖЕ
        return 2*mh.pi-mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) + rm.random()*mh.pi*0.1
    else:           # если точка на картинке находится ВЫШЕ
        return mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) + rm.random()*mh.pi*0.1

# функция добавляет еще один корабль в shmass. присваивает ему заданные координаты, и если угол не задан, корабль летит в центр.
def createShip(shmass, x, y, afa = 10):             # функция для создания корабля, принимает массив кораблей, координаты, направление (опц.)
    if afa == 10:                                   # если афа не задана, то она принимает десятку как знак того, что корабль
        afa = setAngle(x,y,x0,y0)                   # должен лететь в точку x0, y0. 
    shmass.append([x,y,afa]) 

# функция даёт приращение координате каждого корабля вдоль его направления и создаёт в этой точке пучок фотонов.
def moveShip(shmass, fmass, chet):
    for i in range(len(shmass)):
        ship = shmass[i]                                # ship это корабль которому мы даём приращение
        ship[0] = (ship[0] + (bvel*mh.cos(ship[2])))   # даём приращение вдоль x
        ship[1] = (ship[1] + bvel*mh.sin(ship[2]))   # и вдоль y
        if (chet == True):
            createBunch(ship[0], ship[1], fmass, i)             # создаем пучок фотонов в этой точке


# функция даёт приращение координате каждого фотона вдоль его направления.
def movePhot(fmass):
    for b in range (len(fmass)):                    # для каждого пучка...
        f = 0
        while f < len(fmass[b]):             # для каждого фотона из пучка...
            f_afa = fmass[b][f][2]                  # работаем с углом поворота фотона относительно горизонтальной оси, по часовой стрелке!
            x = (fmass[b][f][0] + fv*mh.cos(f_afa))
            y = (fmass[b][f][1] + fv*mh.sin(f_afa))
            if (x <= wth and x >= 0 and y <= lth and y >= 0):
                fmass[b][f][0] = (fmass[b][f][0] + fv*mh.cos(f_afa)) # приращение координат фотона в направлении этого угла
                fmass[b][f][1] = (fmass[b][f][1] + fv*mh.sin(f_afa)) #
            else: 
                del fmass[b][f]
                f -= 1
            f += 1
 # endregion

# region Функции графики

#Функция рисует картинку на месте установки

# функция рисует точку, 
def drawPoints(pmass, color):
    for i in range(len(pmass)):
        point = pmass[i]
        cv.circle(img, (int(point[0]), int(point[1])), pr, color, -1)

# функция рисует установку
def drawStation():
    cv.rectangle(img, (x0 - int(stR*0.75), y0 - int(stR*0.75)), (x0 + int(stR*0.75), y0 + int(stR*0.75)), (1, 0.2, 0), -1)
    cv.rectangle(img, (x0 - int(stR*0.25), y0 - int(stR*0.25)), (x0 + int(stR*0.25), y0 + int(stR*0.25)), (0.4, 0, 0.5), -1)
    cv.rectangle(img, (x0 - int(stR*0.5), y0 + int(stR*0.75)), (x0 + int(stR*0.5), y0 + stR), (0.4, 0, 0.5), -1)
    cv.rectangle(img, (x0 + int(stR*0.75), y0 - int(stR*0.5)), (x0 + stR, y0 + int(stR*0.5)), (0.4, 0, 0.5), -1)
    cv.rectangle(img, (x0 - int(stR*0.5), y0 - stR), (x0 + int(stR*0.5), y0 - int(stR*0.75)), (0.4, 0, 0.5), -1)
    cv.rectangle(img, (x0 - stR, y0 - int(stR*0.5)), (x0 - int(stR*0.75), y0 + int(stR*0.5)), (0.4, 0, 0.5), -1)

# функция рисует корабли, то есть кружки, центры кружков хранятся в shmass, радиус - в глобальной переменной shipsize
def drawShip(shmass, color):       
    for i in range(len(shmass)):
        ship = shmass[i]
        cv.circle(img, (int(ship[0]), int(ship[1])), shipsize, color, -1)

# функция рисует фотоны, то есть кружки, центры кружков хранятся в fmass, радиус - в глобальной переменной fr
def drawPhot(fmass, color):
    for b in range(len(fmass)):
        bunch = fmass[b]
        for f in range(len(bunch)):
            foton = bunch[f]
            if color != (0,0,0):
                if foton[3] == 1:
                    color = (0,1,0)
                elif foton[3] == 2:
                    color = (1, 0, 0)
                elif foton[3] == 3:
                    color = (1, 1, 0)
                else:
                    color = (0.5, 0, 0.5)
            cv.circle(img, (int(foton[0]), int(foton[1])), fr, color, -1)
# endregion

# Обработка физики
def phys(fmass, shmass, pmass, bullets, turret): #Обработка всей физики
    global chet
    #Движение кораблей и испускание ими фотонов
    moveShip(shmass, fmass, chet)
    chet = not chet                         # отвечает за то, нужно ли на этом ходу испустить фотон. фотон испускается раз в два хода
    movePhot(fmass)                         # движение фотонов

    #вытаскиваем координаты кораблей из pmass и пытаемся вызвать функцию Артура, чтобы она их расстреляла
    coordinates = []
    for i in range(len(pmass)):
        if pmass[i][2] == 10:                  # если точка это координата корабля
            coordinates.append(pmass[i])         # добавляем в массив её.
    if (len(coordinates) >= 4):
        bullets.append(turret.fire(coordinates))

    for bullet in bullets:#<A>
        bullet.move()
    abmass = calculate_b(pmass)             # вычисление прямых
    calculate_intersection(pmass, abmass)   # определение точек пересечения по прямым


# Обработка графики
def graph(draw, img, fmass, shmass, pmass, bullets, turret):    # draw: если 1, то закрашиваем, если 0 - то стираем, то есть рисуем черным
    # цвет закрашивания
    if draw == 1:
        color, color1, color2, color3 = (255,255,255), (0,255,255), (0, 0, 255), (255, 0, 0) #белый, желтый, красный, синий
    else:
        color, color1, color2, color3 = (0,0,0), (0,0,0), (0,0,0), (0,0,0) # черный (стираем)

    if draw == 1:                   # нужно чтобы pmass не удалялся перед обработкой физики (физика обрабатывается после стирания)
        clearPmass(pmass)           # стираем старые точки из pmass, кроме тех, что с углом 10. Это третий! элемент. 4-й это номер кор.
    photCollid(fmass, pmass)        # ищем новые столкновения фотонов, заносим в pmass  
    drawStation()
    turret.draw((255,255,0))#отрисовываем турель #<А>
    for bullet in bullets:#<A>
        bullet.draw(color3) 

    drawShip(shmass, color)
    #drawPhot(fmass, color1)         # РИСУЕТ ФОТОНЫ, ЧТОБЫ НЕ РИСОВАТЬ ЗАКОММЕНТИРУЕМ
    drawPoints(pmass, color2)      
    

# Главная функция
def main():

    fmass = [[]]                        # создаём трёхмерный массив, хранящий все пучки, каждый пучок хранит все фотоны, фотоны - 
                                        # свои координаты и угол относительно направления оси x по часовой стрелке.
    shmass = []                         # массив кораблей, хранящий каждый корабль, корабль хранит свои координаты и угол.
    pmass = []                          # массив точек, в него заносится координаты и угол фотонов, проходящих через установку.
    bullets = []
    # Создание кораблей и турелей
    turret1 = Turret((turretR + 5, turretR + 5))    # создаём турель в верхнем левом углу <A>
    createShip(shmass, 50, 50)
    # createShip(shmass, wth - 50, 100)             # создание еще кораблей по углам
    # createShip(shmass, wth - 50, lth - 50)        #
    # createShip(shmass, 50, lth - 50)              #

    for t in range(100): # выполняем программу в течение стольких итераций
        graph(0, img, fmass, shmass, pmass, bullets, turret1)    # стираем старое
        phys(fmass, shmass, pmass, bullets, turret1)     # изменяем координаты в соответствии со скоростями
        graph(1, img, fmass, shmass, pmass, bullets, turret1)    # рисуем новое
    
        cv.imshow(wname, img)           
        cv.waitKey(1)

cv.namedWindow(wname, cv.WINDOW_NORMAL) # создаём окно размером 1280 на 720
cv.resizeWindow(wname, 1280, 720)       #
img = np.zeros((lth, wth, 3))           # Массив для самой картинки, с кораблями и фотонами и установкой

main() 
