import os
from skimage.transform import resize,rotate
from skimage.io import imread
from numpy.random import random
import numpy as np
from sklearn.model_selection import  train_test_split,GridSearchCV
from sklearn import svm
from sklearn.metrics import accuracy_score,classification_report

from joblib import dump,load

#用来保持对应的处理好的图像数据和对应的类型分类列表
flat_data_arr = []
target_arr = []
#用来保持对应的处理好的图像数据和对应的类别分类numpy数组
flat_data = ''
target = ''
#模型的名称
mode = "model.joblib"




#定义存放图片的路径
datadir = './DATA/'
#识别的种类【apple banana】
Categories = ['apple' , 'banana']


#加载对应的数据
def loading_data():
    for i in Categories:
        print(f'loading... category:{i}')
        #路径拼接
        path = os.path.join(datadir,i)
        #遍历整个目录中文件
        for img in os.listdir(path):
            #这里把图像转为对应的图像数组
            img_array = imread(os.path.join(path,img))
            print(img_array)
            #确保后面的格式为RGB，确保只有三个通道
            if len(img_array.shape) !=3 or img_array.shape[2] !=3:
                print(f'图像{img}的格式不合法,非RGBG模式，跳过图像')
                continue

            img_resized = resize(img_array,(150,150,3),anti_aliasing=True)
            #随机的旋转角度再30和-30之间，概率是50%
            if random() > 0.5:
                img_resized = rotate(img_resized,angle=np.random.randint(-30,30))

            if random() > 0.5:
                #进行对应的水平翻转
                img_resized = np.fliplr(img_resized)

            #把图像数据展开为一维数组，添加进入列表
            flat_data_arr.append(img_resized.flatten())
            #加入对应的索引下标
            target_arr.append(Categories.index(i))


        global flat_data
        global target
        # 把list转为numpy数组保存起来，方便后面处理
        flat_data = np.array(flat_data_arr)
        target = np.array(target_arr)

        #数据的归一化，把数据归一为【0,1】
        flat_data = flat_data / 255.0
        print(flat_data)




def deal_data():
    x_train,x_test,y_train,y_test = train_test_split(flat_data,target,test_size=0.3,random_state=42)


    #超参数调优
    param_grid = {
        'C': [0.1, 1, 10],  # 这里添加了逗号，用于分隔不同的键值对
        'kernel': ['linear', 'rbf']
    }

    clf = svm.SVC()

    grid_Search = GridSearchCV(clf,param_grid,cv=5)

    grid_Search.fit(x_train,y_train)

    best_clf = grid_Search.best_estimator_

    best_clf.fit(x_train,y_train)

    y_pred = best_clf.predict(x_test)

    accuracy = accuracy_score(y_test,y_pred)
    print(f'准确率{accuracy}')
    #打印一些详细的分类指标
    print(classification_report(y_test,y_pred))

    #保存一下对应的模型
    dump(best_clf,mode)


if __name__ == "__main__":
    loading_data()
    deal_data()