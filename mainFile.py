import numpy as np
import cv2 as cv
import math as mh
import time as ti
import random as rm
import copy

# region Глобальные переменные
wname = 'Guardian Station'  # Название окна
shipsize = 9                # размер корабля                
fcnt = 500                  # Количество фотонов в пучке
fv = 50                     # Скорость фотонов
bvel = 3                    # Скорость кораблей
fr = 1                      # Радиус фотонов
wth = int(1*1280)           # Ширина окна (разрешение)
lth = int(1*720)            # Высота
x0 = int(wth/2)             # Центр карты, центр установки
y0 = int(lth/2)             # 
stR = 40                    # Радиус установки
pr = 1                      # Радиус точки из массива pmass
chet = True                 # Меняя эту переменную, сделаем испускание фотонов раз в два кадра.
hp_0 = 4                    # Количество жизней
hp = hp_0
shN = 0                     # Переменная для количества кораблей
abmass_todraw = []          # Массив для рисования прямых
switch = [0, 0, 0]          # Массив для пункта меню Settings -> Drawing. Изначально заполнен единицами, то есть рисуем всё
turretR = 22                # размер турели
bulletSpeed = 22            # скорость снаряда
bulletR = 8                 # радиус снаряда
shnum = 5                   # Изначальное количество кораблей, не меняется во время симуляции
ct = 40                     # период цикла

# region Классы
class Turret():                         #класс турели
    def __init__(self, coordinates):    #при создании новой турели задаём её координаты
        self.x, self.y = coordinates
    def draw(self, color):              #рисуем турель # <D>
        if color == (0,0,0):
            color1, color2 = color, color
        else:
            color1, color2 = (1, 0.2, 0), (0.4, 0, 0.5) 
        x = self.x
        y = self.y
        mp = 1
        if x > wth*0.5:
            mp = -1
        tR = turretR
        cv.fillPoly(img, [np.array([[x+mp*(0.25*tR),y], [x+mp*(2*tR), y+0.5*tR], [x+mp*(1.25*tR), y-0.25*tR], ], np.int32)], color2)
        cv.fillPoly(img, [np.array([[x-mp*(0.25*tR),y], [x+mp*(0.5*tR), y+2*tR], [x-mp*(0.25*tR), y+1.25*tR], ], np.int32)], color2)
        cv.circle(img, (x,y), int(tR), color2, -1)
        cv.circle(img, (x,y), int(0.6*tR), color1, int(0.3*tR))
        
    def get_target_location(self, coordinates):
        #Получаем точку, в которую надо стрелять следующим образом: находим t, при котором |r(t) - vt| < bulletR - 3, где v - скорость снаряда,
        #при достаточном размере снаряда (или при большом массиве точек траектории), гарантированно попадаем
        global bulletSpeed
        tmin = 0
        range_min = 10000
        for t in range(len(coordinates)):
            if abs(((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - 2 * bulletSpeed * t) < range_min:
                tmin = t
                range_min = abs(((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - 2 * bulletSpeed * t)
                if range_min < bulletSpeed:
                    break
        return(coordinates[tmin + 1])
    def fire(self, coordinates):        #Стреляем по координатам корабля, возвращаем объект типа bullet
        return Bullet((self.x, self.y), self.get_target_location(coordinates))
  
class Bullet():
    def __init__(self, start, target):  #инициализируем снаряд, задавая начальную точку и точку прилёта снаряда, находим проекцию скоростей
        r = ((start[0] - target[0]) ** 2 + (start[1] - target[1]) ** 2) ** 0.5
        self.x_speed = int((target[0] - start[0]) * bulletSpeed / r)
        self.y_speed = int((target[1] - start[1]) * bulletSpeed / r)
        self.x = start[0]
        self.y = start[1]
    def draw(self, color):              #рисуем снаряд
        if color == (0,0,0):
            color1 = color
        else:
            color1 = (0.2, 0, 1)
        bR = 1.3*bulletR
        cv.circle(img, (self.x,self.y), int(bR), color1, int(bR*0.2))
        cv.circle(img, (self.x,self.y), int(0.4*bR), color1, -1)        

    def move(self):                     #сдвигаем снаряд, соответственно его времени
        self.x += self.x_speed
        self.y += self.y_speed
        if (self.x <= 0 or self.x >= wth or self.y <= 0 or self.y >= lth):
            return 1
        else:
            return 0
#endregion 

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
        while i < len(abmass):                  # пока мы не дошли до конца и пока мы не усреднили координату с 5 соседями#<A>
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

        f = 0                                                   # флаг
        if (ctr >= 4):                                          # если учтено больше трёх пересечений (их не обязательно 5)
            if ((x0 - coord[0])**2 + (y0 - coord[1])**2)**0.5 < stR*3:
                f = 1
            for i in range (len(pmass)):
                if (pmass[i][2] == 10 and pmass[i][3] == nbr):
                    if ((pmass[i][0] - coord[0])**2 + (pmass[i][1] - coord[1])**2)**0.5 < 0.9*bvel or ((x0 - coord[0])**2 + (y0 - coord[1])**2)**0.5 < stR*3:
                        f = 1
            if f == 0:
                pmass.append([coord[0], coord[1], 10, nbr])         # добавляем точку в pmass с номером корабля, испустившего фотон 

def drawABmass(abmass_todraw, color):
    for i in range(len(abmass_todraw)):
        a = abmass_todraw[i][0]
        b = abmass_todraw[i][1]

        if (b > 0):
            pt1 = (0,b)
        else:
            pt1 = (-b/a, 0)
        if a*wth + b < lth:
            pt2 = (wth, a*wth + b)
        else:
            pt2 = ((lth - b)/a, lth)
        
        cv.line(img, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), color, 1)

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
        foton[0] = x                                # присваиваем координаты из аргументов
        foton[1] = y
        foton[2] = 2*mh.pi*(i/fcnt)
        foton[3] = nbr                              #четвёртый параметр отвечает за корабль, от которого фотон отлетел
    
# функция возвращает угол между вектором с началом в точке (x, y) концом в точке (x1, y1) и вектором, направленным вдоль оси x
def setAngle(x,y,x1,y1):  
    # условие нужно, чтобы устранить неопределенность в знаке при вычислении из скалярного произведения 
    if (y1-y) < 0:          # если точка имеет большую, чем точка 1, координату по y, то есть на картинке она НИЖЕ
        return 2*mh.pi-mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) 
    else:                   # если точка на картинке находится ВЫШЕ
        return mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2))))

# функция добавляет еще один корабль в shmass. присваивает ему случайную координату выбранную достаточно далеко от установки
def createShipRand(shmass, afa = 10):             # функция для создания корабля, принимает массив кораблей, координаты, направление (опц.)
    global shN
    #функция рандома работает для одного отрезка, но у нас их два, потому что установка в середине окна
    #поэтому временно как бы смещаем установку к правому краю и вычисляем от одного отрезка
    #если значение попало в область "эллипса", то смещаем его, чтобы было там, где по идее должно быть
    x = rm.randint(0, wth/2)
    if (wth/4 <= x <= wth/2):
        x += wth/2
    y = rm.randint(0, lth/2)
    if (lth/4 <= y <= lth/2):
        y += lth/2
    if afa == 10:                                   # если афа не задана, то она принимает десятку как знак того, что корабль
        afa = setAngle(x,y,x0,y0)                   # должен лететь в точку x0, y0. 
    shmass.append([x,y,afa,shN]) 
    shN += 1

def createShip(shmass, x, y, afa = 10):             # функция для создания корабля, принимает массив кораблей, координаты, направление (опц.)
    global shN
    if afa == 10:                                   # если афа не задана, то она принимает десятку как знак того, что корабль
        afa = setAngle(x,y,x0,y0)                   # должен лететь в точку x0, y0. 
    shmass.append([x,y,afa,shN]) 
    shN += 1

# функция даёт приращение координате каждого корабля вдоль его направления и создаёт в этой точке пучок фотонов.
def moveShip(shmass, fmass, chet):
    for i in range(len(shmass)):
        ship = shmass[i]                                # ship это корабль которому мы даём приращение
        ship[0] = (ship[0] + (bvel*mh.cos(ship[2])))    # даём приращение вдоль x
        ship[1] = (ship[1] + bvel*mh.sin(ship[2]))      # и вдоль y
        if (chet == True):
            createBunch(ship[0], ship[1], fmass, ship[3])     # создаем пучок фотонов в этой точке

# функция даёт приращение координате каждого фотона вдоль его направления.
def movePhot(fmass):
    for b in range (len(fmass)):                    # для каждого пучка...
        f = 0
        while f < len(fmass[b]):                    # для каждого фотона из пучка...
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

# функция детектит столкновения кораблей с установкой и уничтожает их 
def shipCollid(shmass):
    global hp, shN
    i = 0
    while i < len(shmass):
        if ((shmass[i][0]-x0)**2+(shmass[i][1]-y0)**2)**0.5 <= stR:
            shmass.pop(i)
            shN -= 1
            hp -= 1
            print("Station hit: health " + str(hp))
            i -= 1
        i += 1

# функция детектит столкновения снаряда с кораблями и уничтожает корабли и пули при столкновении.
# ЧТОБЫ ПОВЫСИТЬ РАДИУС ДЛЯ ТЕСТА - УВЕЛИЧЬТЕ МНОЖИТЕЛЬ ВОЗЛЕ ЧИСЛА (bulletR + shipsize)
def bullCollid(bullets, shmass):
    i = 0
    while i < len(shmass):
        j = 0
        while j < len(bullets):
            if ( (bullets[j].x - shmass[i][0])**2 + (bullets[j].y - shmass[i][1])**2 )**0.5 <= 1*(bulletR + shipsize):
                global shN
                shmass.pop(i)
                bullets.pop(j)
                shN -= 1
                print ("Ship " + str(i) + " destroyed, ships remained: " + str(shN))
                j -= 1
                i -= 1
                break
            j += 1
        i += 1

# функция подаёт сигнал на завершение симуляции, если установка мертва либо кораблей ноль.
def simEnd():
    if hp == 0:
        print ("Station Destroyed")
        return 1
    if shN == 0:
        print ("Ships Destroyed")
        return 1
    return 0
# endregion

# region Функции графики

# функция добавляет координаты предсказанных положений в pmass с углом 11. нужно чтобы их нарисовать, и чтобы они стёрлись потом.
def drawPredict(pmass):
    flag = 11
    for j in range (shnum):
        cds = []
        for i in range(len(pmass)):
            if pmass[i][2] == 10:            # если точка это координата корабля
                if pmass[i][3] == j:
                    flag = 0
                    cds.append(pmass[i])         # добавляем в массив её.
        if len(cds) > 4:                       # если мы получили больше 4 точек, добавляем их в pmass, чтобы нарисовать
            prediction = predict(cds) 
            for i in range(len(prediction)):
                pmass.append([prediction[i][0], prediction[i][1], 11, -1])
        if flag == 1:
            break

# функция рисует точки из pmass
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
    if color == (0,0,0):
        color1, color2 = color, color
    else:
        color1, color2 = (1, 0.2, 0), (0.2, 0, 1)       
    for i in range(len(shmass)):
        ship = shmass[i]
        x = shmass[i][0]
        y = shmass[i][1]
        shR = shipsize*1.5
        cv.rectangle(img, (int(x-shR), int(y-0.25*shR)), (int(x+shR), int(y+0.25*shR)), color1, -1)
        cv.fillPoly(img, [np.array([[x-0.5*shR,y], [x,y+0.5*shR],[x+0.5*shR,y],[x,y-0.5*shR]], np.int32)], color2)
        cv.fillPoly(img, [np.array([[x-0.75*shR, y-shR], [x-0.75*shR, y+shR], [x-1.25*shR, y+0.25*shR], [x-1.25*shR, y-0.25*shR]], np.int32)], color2)
        cv.fillPoly(img, [np.array([[x+0.75*shR, y-shR], [x+0.75*shR, y+shR], [x+1.25*shR, y+0.25*shR], [x+1.25*shR, y-0.25*shR]], np.int32)], color2)
        
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

#функция возвращает правую турель, если корабль в правой половине, и соотв. с левой
def choose_turret(turrets, coordinates):
    if coordinates[0][0] < wth / 2:
        return turrets[0]
    return turrets[1]

# функция берёт массив зарегистрированных точек, и возвращает массив с координатами, начиная с позиции корабля в текущий момент и в будущем
def predict(coordmass):
    p1 = coordmass[0]
    p2 = coordmass[len(coordmass)-1]
    
    afa = setAngle(p1[0], p1[1], p2[0], p2[1])

    dx = 0
    dy = 0

    dx_1 = 0
    dy_1 = 0

    while (((p2[0]+dx-x0)**2 + (p2[1]+dy-y0)**2)**0.5) >= stR:
        dx += mh.cos(afa)*fv
        dy += mh.sin(afa)*fv
        dx_1 += mh.cos(afa)*bvel
        dy_1 += mh.sin(afa)*bvel

    prediction = [[p2[0]+dx_1, p2[1]+dy_1]]
    for i in range (0, 40):
        prediction.append([prediction[i][0] + mh.cos(afa)*2*bvel, prediction[i][1]+ mh.sin(afa)*2*bvel])
    return prediction

#выводит итог работы: время, количество оставшихся кораблей, количество кораблей изначальное, и итог: победа установки или кораблей.

def print_result(shmass, t):
    print("Time: ", t)
    print("Start number of ships: ", shnum)
    print("Number of remaining ships: ", len(shmass))
    if hp == 0:
        print("Ships won")
    else:
        print("Station won")
    
      
# ОБРАБОТКА ФИЗИКИ
def phys(fmass, shmass, pmass, bullets, turrets):
    global chet, coordinates, abmass_todraw, shot_flag        # некоторые глобальные переменные
    bullCollid(bullets, shmass)
    shipCollid(shmass)                      # уничтожает столкнувшиеся с установкой корабли
    moveShip(shmass, fmass, chet)           # двигает установку
    chet = not chet                         # отвечает за то, нужно ли на этом ходу испустить фотон. фотон испускается раз в два хода
    movePhot(fmass)                         # движение фотонов

    # вызов стрельбы
    for i in pmass:
        if i[2] != 10:  # аналогично if pmass[i][2] == 10:                    # если точка это координата корабля
            continue
        if(len(coordinates[i[3]]) > -1 ):
            pass
        if(shot_flag[i[3]] > -1 ):
            pass
        if (len(coordinates[i[3]]) < 4 + 16*shot_flag[i[3]]):                                   #Ищем 4 точки от одного корабля
            if tuple([i[0], i[1]]) not in coordinates[i[3]]:
                coordinates[i[3]].append(tuple([i[0], i[1]]))
            continue
        if (len(coordinates[i[3]]) == 4 + 16*shot_flag[i[3]]):                                  #Если есть 4, то можем продолжить прямую
            coordinates[i[3]] = predict(coordinates[i[3]])                                      #Заменяем полученные несколько точек в координатах на продолжение данной прямой#<A>
            bullets.append(choose_turret(turrets, coordinates[i[3]]).fire(coordinates[i[3]]))
            while len(coordinates[i[3]])>0:
                coordinates[i[3]].pop(0)
            shot_flag[i[3]] = 1
            d = 0
            while d < len(pmass):
                if pmass[d][3] == i[3]:
                    pmass.pop(d)
                    d -= 1
                d += 1

    i = 0                                   # движение снарядов
    while i < len(bullets):                 
        if (bullets[i].move() == 1):                
            bullets.pop(i)                          
            i -= 1
        i += 1

    if switch[2] == 1:
        if (len(abmass_todraw) != 0):                   # рисование линий из abmass
            drawABmass (abmass_todraw, (0,0,0))         # рисование линий из abmass
    abmass = calculate_b(pmass)                         # вычисление прямых
    if switch[2] == 1:
        abmass_todraw = copy.deepcopy(abmass)           # рисование линий из abmass
        drawABmass (abmass, (255,255,255))              # рисование линий из abmass

    calculate_intersection(pmass, abmass)   # определение точек пересечения по прямым
    
# Обработка графики
def graph(draw, img, fmass, shmass, pmass, abmass_todraw, bullets, turrets, switch):    # draw: если 1, то закрашиваем, если 0 - то стираем, то есть рисуем черным 
    # цвет закрашивания
    if draw == 1:
        color, color1, color2, color3 = (255,255,255), (0,255,255), (0, 0, 255), (255, 0, 0) #белый, желтый, красный, синий
    else:
        color, color1, color2, color3 = (0,0,0), (0,0,0), (0,0,0), (0,0,0) # черный (стираем)

    if draw == 1:                   # нужно чтобы pmass не удалялся перед обработкой физики (физика обрабатывается после стирания)
        clearPmass(pmass)           # стираем старые точки из pmass, кроме тех, что с углом 10. Это третий! элемент. 4-й это номер кор.
    photCollid(fmass, pmass)        # ищем новые столкновения фотонов, заноqсим в pmass  
    drawStation()
    for i in turrets:
        i.draw((255,255,0))         # отрисовываем турели 
    for bullet in bullets:
        bullet.draw(color3) 

    # РИСОВАНИЕ PREDICT
    drawPredict (pmass)
    drawShip(shmass, color)
    if switch[0] == 1:
        drawPhot(fmass, color1)     # РИСУЕТ ФОТОНЫ
    if switch[1] == 1:
        drawPoints(pmass, color2)
        
# Главная функция
def main():
    global coordinates, bulletR, bulletSpeed, bvel, img, abmass_todraw, switch, shnum, hp, shot_flag, ct #глобальные переменные чтобы их менять
    
    # НАЧАЛО ВЫПОЛНЕНИЯ:
    cv.namedWindow(wname, cv.WINDOW_NORMAL) # создаём окно размером 1280 на 720
    cv.resizeWindow(wname, 1280, 720)       #
    img = np.zeros((lth, wth, 3))           # Массив для самой картинки, с кораблями и фотонами и установкой

    hp = hp_0    
    shot_flag = np.zeros(shnum, np.int32)
    
    coordinates = []
    fmass = [[]]                        # создаём трёхмерный массив, хранящий все пучки, каждый пучок хранит все фотоны
    shmass = []                         # массив кораблей, хранящий каждый корабль, корабль хранит свои координаты и угол.
    pmass = []                          # массив точек, в него заносится координаты и угол фотонов, проходящих через установку.
    bullets = [] 
    abmass_todraw = []                       
    # Создание турелей
    turrets = []                                                # массив всех турелей 
    turrets.append(Turret((turretR + 5, turretR + 5)))          # создаём турель в верхнем левом углу 
    turrets.append(Turret((wth - 5 - turretR, turretR + 5)))    # создаём турель в верхнем правом углу 

    
    # Создаем корабли
    for i in range(shnum):
        createShipRand(shmass)
              
    print ("Health: " + str(hp))
    print ("Ship Number: " + str(shN))
    
    for i in range(shnum):
        coordinates.append([])
        
    for t in range(1000): # выполняем программу в течение стольких итераций
        graph(0, img, fmass, shmass, pmass, abmass_todraw, bullets, turrets, switch)    # стираем старое 
        phys(fmass, shmass, pmass, bullets, turrets)                                    # изменяем координаты в соответствии со скоростями 
        graph(1, img, fmass, shmass, pmass, abmass_todraw, bullets, turrets, switch)    # рисуем новое 
        cv.imshow(wname, img)   
        key = cv.waitKey(ct) & 0xFF
        if (key == ord('q')) or simEnd() == 1:
            cv.destroyAllWindows()
            break
        if (key == ord('p')):
            cv.waitKey()
            

    print_result(shmass, t)
    # КОНЕЦ ВЫПОЛНЕНИЯ        

#Вспомогательные функции для меню
def speed_and_size():
    global bvel, bulletSpeed, bulletR, shnum, ct
    print("1. Change ships speed\n2. Change ships number\n3. Change bullet speed\n4. Change bullet size\n5. Change cycle time\n6. Go back")
    choice = input()
    if choice == "1":
        print("Enter ships speed ")
        bvel = int(input())
        speed_and_size()
    if choice == "2":
        print("Enter amount of ships")
        shnum = int(input())
        speed_and_size()
    if choice == "3":
        print("Enter bullet speed ")
        bulletSpeed = int(input())
        speed_and_size()
    if choice == "4":
        print("Enter bullet radius ")
        bulletR = int(input())
        speed_and_size()
    if choice == "5":
        print("Enter new cycle time ")
        ct = int(input())
        speed_and_size()
    if choice == "6":
        settings()

def drawing():
    global switch

    print("\n1. Draw photons\n2. Do not draw photons\n3. Draw points\n4. Do not draw points\n5. Draw paths\n6. Do not draw paths\n7. Go back")
    choice = input()
    if choice == "1":
        switch[0] = 1
        drawing()
    if choice == "2":
        switch[0] = 0
        drawing()
    if choice == "3":
        switch[1] = 1
        drawing()
    if choice == "4":
        switch[1] = 0
        drawing()
    if choice == "5":
        switch[2] = 1
        drawing()
    if choice == "6":
        switch[2] = 0
        drawing()
    if choice == "7":
        settings()

def settings():
    print("\n1. Numerical parameters\n2. Drawing\n3. Go back")
    choice = input()
    if choice == "1":
        speed_and_size()
    if choice == "2":
        drawing()
    if choice == "3":
        menu()
#МЕНЮ
def menu():
    print("\n1. Start Simulation\n2. Quit\n3. Settings")
    choice = input()
    if choice == "1":
        main()
        menu()
    if choice == "2":
        return 1
    if choice == "3":
        settings()

menu()
