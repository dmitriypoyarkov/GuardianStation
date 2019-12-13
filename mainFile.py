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
bvel = 5                   # Скорость кораблей
fr = 1                      # Радиус фотонов
wth = int(1*1280)           # Ширина окна (разрешение)
lth = int(1*720)            # Высота
x0 = int(wth/2)             # Центр карты, центр установки
y0 = int(lth/2)             # 
stR = 40                    # Радиус установки
pr = 1                      # Радиус точки из массива pmass
chet = True                 # Меняя эту переменную, сделаем испускание фотонов раз в два кадра.
hp = 4                      # Количество жизней
shN = 0
abmass_todraw = []

turretR = 22                # размер турели
bulletSpeed = 22            # скорость снаряда
bulletR = 11                # радиус снаряда


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
        tmin = 0
        range_min = 10000
        for t in range(len(coordinates)):
            print (t)
            print(((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - bulletSpeed * t)
            if (abs((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - bulletSpeed * t) < bulletR - 3:
                tmin = t
                #range_min = abs(((self.x - coordinates[t][0]) ** 2 + (self.y - coordinates[t][1]) ** 2) ** 0.5 - bulletSpeed * t)
                #break
        #print(coordinates[tmin])
        return(coordinates[tmin])
    def fire(self, coordinates):        #Стреляем по координатам корабля, возвращаем объект типа bullet
        return Bullet((self.x, self.y), self.get_target_location(coordinates))
  
class Bullet():
    def __init__(self, start, target):  #инициализируем снаряд, задавая начальную точку и точку прилёта снаряда, находим проекцию скоростей
        r = ((start[0] - target[0]) ** 2 + (start[1] - target[1]) ** 2) ** 0.5
        self.x_speed = int((target[0] - start[0]) * bulletSpeed / r)
        self.y_speed = int((target[1] - start[1]) * bulletSpeed / r)
        self.x = start[0]
        self.y = start[1]
    def draw(self, color):              #рисуем снаряд # <D>
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

        # <D>
        if (self.x <= 0 or self.x >= wth or self.y <= 0 or self.y >= lth):
            return 1
        else:
            return 0
        # </D>
#endregion 

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

        if (ctr >= 3):                                          # если учтено больше трёх пересечений (их не обязательно 5)
            pmass.append([coord[0], coord[1], 10, nbr])         # добавляем точку в pmass с номером корабля, испустившего фотон 

def drawABmass(abmass, color):
    for i in range(len(abmass)):
        a = abmass[i][0]
        b = abmass[i][1]

        if (b > 0):
            pt1 = (0,b)
        else:
            pt1 = (-b/a, 0)
        if a*wth + b < lth:
            pt2 = (wth, a*wth + b)
        else:
            pt2 = ((lth - b)/a, lth)
        
        cv.line(img, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), color, 1)
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

# функция возвращает угол между вектором с началом в точке (x, y) концом в точке (x1, y1) и вектором, направленным вдоль оси x
# с разбросом в +/- 45 градусов
def setAngleRand(x,y,x1,y1):  
    # условие нужно, чтобы устранить неопределенность в знаке при вычислении из скалярного произведения 
    if (y1-y) < 0:          # если точка имеет большую, чем точка 1, координату по y, то есть на картинке она НИЖЕ
        return 2*mh.pi-mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) + rm.random()*mh.pi*0.1
    else:                   # если точка на картинке находится ВЫШЕ
        return mh.acos((x1-x)/(mh.sqrt(mh.pow(x1-x,2)+mh.pow(y1-y,2)))) + rm.random()*mh.pi*0.1

# функция добавляет еще один корабль в shmass. присваивает ему заданные координаты, и если угол не задан, корабль летит в центр.
def createShip(shmass, x, y, afa = 10):             # функция для создания корабля, принимает массив кораблей, координаты, направление (опц.)
    global shN
    if afa == 10:                                   # если афа не задана, то она принимает десятку как знак того, что корабль
        afa = setAngle(x,y,x0,y0)                   # должен лететь в точку x0, y0. 
    shmass.append([x,y,afa]) 
    shN += 1

# функция даёт приращение координате каждого корабля вдоль его направления и создаёт в этой точке пучок фотонов.
def moveShip(shmass, fmass, chet):
    for i in range(len(shmass)):
        ship = shmass[i]                                # ship это корабль которому мы даём приращение
        ship[0] = (ship[0] + (bvel*mh.cos(ship[2])))    # даём приращение вдоль x
        ship[1] = (ship[1] + bvel*mh.sin(ship[2]))      # и вдоль y
        if (chet == True):
            createBunch(ship[0], ship[1], fmass, i)     # создаем пучок фотонов в этой точке


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
    for i in range(len(shmass)):
        if ((shmass[i][0]-x0)**2+(shmass[i][1]-y0)**2)**0.5 <= stR:
            shmass.pop(i)
            shN -= 1
            hp -= 1
            print("Station hit: health " + str(hp))

# функция детектит столкновения снаряда с кораблями и уничтожает корабли и пули при столкновении.
# ЧТОБЫ ПОВЫСИТЬ РАДИУС ДЛЯ ТЕСТА - УВЕЛИЧЬТЕ МНОЖИТЕЛЬ ВОЗЛЕ ЧИСЛА (bulletR + shipsize)
def bullCollid(bullets, shmass):
    
    for i in range (len(shmass)):
        for j in range (len(bullets)):
            if ( (bullets[j].x - shmass[i][0])**2 + (bullets[j].y - shmass[i][1])**2 )**0.5 <= 1*(bulletR + shipsize): # МОЖНО ПОВЫСИТЬ
                global shN
                shmass.pop(i)
                bullets.pop(j)
                shN -= 1
                print ("Ship " + str(i) + " destroyed, ships remained: " + str(shN))

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
    cds = []                             # массив для полученных координат
    for i in range(len(pmass)):
        if pmass[i][2] == 10:            # если точка это координата корабля
            cds.append(pmass[i])         # добавляем в массив её.
            
    if len(cds)>4:                       # если мы получили больше 4 точек, добавляем их в pmass, чтобы нарисовать
        prediction = predict(cds)           
        for i in range(len(prediction)):
            pmass.append([prediction[i][0], prediction[i][1], 11, -1])

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
        #cv.circle(img, (int(ship[0]), int(ship[1])), shipsize, color, -1)

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


# ОБРАБОТКА ФИЗИКИ
def phys(fmass, shmass, pmass, bullets, turrets):
    global chet, coordinates, abmass_todraw        # некоторые глобальные переменные

    bullCollid(bullets, shmass)
    shipCollid(shmass)                      # уничтожает столкнувшиеся с установкой корабли
    moveShip(shmass, fmass, chet)           # двигает установку
    chet = not chet                         # отвечает за то, нужно ли на этом ходу испустить фотон. фотон испускается раз в два хода
    movePhot(fmass)                         # движение фотонов
    
    # вызов стрельбы
    for i in pmass:
        if (i[3] == 10):
            print('a', i[0], i[1])
        if i[2] != 10:# аналогично if pmass[i][2] == 10:                  # если точка это координата корабля
            continue
        if (len(coordinates[i[3]]) < 5):#Ищем 4 точки от одного корабля
            if tuple([i[0], i[1]]) not in coordinates[i[3]]:
                coordinates[i[3]].append(tuple([i[0], i[1]]))
            pmass.remove(i)
            continue
        if (len(coordinates[i[3]]) == 5):#Если есть 4, то можем продолжить прямую
            #coordinates[i[3]].append(i)
            '''for j in coordinates[i[3]]:
                '''#НАДО ДОПИСАТЬ'''
                
            coordinates[i[3]] = predict(coordinates[i[3]])#Заменяем полученные несколько точек в координатах на продолжение данной прямой#<A>
            bullets.append(choose_turret(turrets, coordinates[i[3]]).fire(coordinates[i[3]]))

    for i in range (len(bullets)):                  # движение снарядов <D>
        if (bullets[i].move() == 1):                # <D>
            bullets.pop(i)                          # <D>

    #if (len(abmass_todraw) != 0):                  # Закомментированное рисование линий из abmass
    #    drawABmass (abmass_todraw, (0,0,0))        # Закомментированное рисование линий из abmass

    abmass = calculate_b(pmass)             # вычисление прямых

    # abmass_todraw = copy.deepcopy(abmass)         # Закомментированное рисование линий из abmass
    #drawABmass (abmass, (255,255,255))             # Закомментированное рисование линий из abmass

    calculate_intersection(pmass, abmass)   # определение точек пересечения по прямым
    
# Обработка графики
def graph(draw, img, fmass, shmass, pmass, bullets, turrets):    # draw: если 1, то закрашиваем, если 0 - то стираем, то есть рисуем черным 
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
    #drawPhot(fmass, color1)         # РИСУЕТ ФОТОНЫ, ЧТОБЫ НЕ РИСОВАТЬ ЗАКОММЕНТИРУЕМ
    drawPoints(pmass, color2)      
    

# Главная функция
def main():
    global coordinates, bulletR, bulletSpeed, bvel, img, abmass_todraw #глобальные переменные чтобы их менять


    # НАЧАЛО ВЫПОЛНЕНИЯ:
    cv.namedWindow(wname, cv.WINDOW_NORMAL) # создаём окно размером 1280 на 720
    cv.resizeWindow(wname, 1280, 720)       #
    img = np.zeros((lth, wth, 3))           # Массив для самой картинки, с кораблями и фотонами и установкой

    coordinates = []
    fmass = [[]]                        # создаём трёхмерный массив, хранящий все пучки, каждый пучок хранит все фотоны
    shmass = []                         # массив кораблей, хранящий каждый корабль, корабль хранит свои координаты и угол.
    pmass = []                          # массив точек, в него заносится координаты и угол фотонов, проходящих через установку.
    bullets = [] 
    abmass_todraw = []                       
    # Создание кораблей и турелей
    turrets = []                        # массив всех турелей 

    turrets.append(Turret((turretR + 5, turretR + 5))) # создаём турель в верхнем левом углу 
    turrets.append(Turret((wth - 5 - turretR, turretR + 5))) #создаём турель в верхнем правом углу 
    #turrets.append(Turret((turretR + 5, lth)))
    #createShip(shmass, 50, 50)
    #createShip(shmass, 500, 500)
    createShip(shmass, wth - 50, 100)               # создание еще кораблей по углам
    #createShip(shmass, wth - 10, lth - 50)         #
    #createShip(shmass, 50, lth - 50)               #
    print ("Health: " + str(hp))
    print ("Ship Number: " + str(shN))
    
    for i in shmass:
        coordinates.append([])
    for t in range(1000): # выполняем программу в течение стольких итераций
        graph(0, img, fmass, shmass, pmass, bullets, turrets)    # стираем старое 
        phys(fmass, shmass, pmass, bullets, turrets)     # изменяем координаты в соответствии со скоростями 
        graph(1, img, fmass, shmass, pmass, bullets, turrets)    # рисуем новое 
        cv.imshow(wname, img)           
        if (cv.waitKey(10) & 0xFF == ord('q')) or simEnd() == 1:# Программа завершается при нажатии q, смерти установки, смерти всех кораблей
            cv.destroyAllWindows()
            break
    # КОНЕЦ ВЫПОЛНЕНИЯ        




main() 
