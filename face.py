import cv2
import numpy as np
import os
import math


def distance(x1, x2):
    """
    计算两个向量之间的欧式距离
    """
    return math.sqrt(np.sum((x1 - x2) ** 2))


def knn(train, test, k=5):
    """
    K近邻算法实现
    """
    dist = []
    for i in range(train.shape[0]):
        ix = train[i, :-1]
        iy = train[i, -1]
        d = distance(test, ix)
        dist.append([d, iy])
    dk = sorted(dist, key=lambda x: x[0])[:k]
    labels = np.array(dk)[:, -1]
    output = np.unique(labels, return_counts=True)
    index = np.argmax(output[1])
    return output[0][index]


def collect_face_data():
    """
    从摄像头采集人脸数据并保存到本地文件
    """
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_alt.xml")

    skip = 0
    face_data = []
    dataset_path = './humanface/'

    file_name = input("Enter the name of person :")

    while True:
        ret, frame = cap.read()
        if ret == False:
            continue

        grey_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(frame, 1.3, 5)
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)

        for face in faces:
            x, y, w, h = face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

            offset = 10
            face_section = frame[y - offset:y + h + offset, x - offset:x + w + offset]
            face_section = cv2.resize(face_section, (100, 100))

            skip += 1
            if skip % 10 == 0:
                face_data.append(face_section)
                print(len(face_data))

            cv2.imshow("face section", face_section)

        cv2.imshow("Frame", frame)
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    face_data = np.asarray(face_data)
    face_data = face_data.reshape((face_data.shape[0], -1))
    np.save(dataset_path + file_name + '.npy', face_data)
    print("Data Succesfully save at " + dataset_path + file_name + '.npy')
    return


def prepare_data():
    """
    加载已保存的人脸数据及对应标签，构建训练集
    """
    face_data2 = []
    labels = []
    class_id = 0  # 标签，用于标识不同的人物
    names = {}  # 用于建立人物id和姓名的映射
    dataset_path = './humanface/'

    for fx in os.listdir(dataset_path):
        if fx.endswith('.npy'):
            names[class_id] = fx[:-4]
            print("Loaded " + fx)

            data_item = np.load(dataset_path + fx)
            face_data2.append(data_item)

            # 创建对应的数据标签
            target = class_id * np.ones((data_item.shape[0],))
            class_id += 1
            labels.append(target)

    face_dataset = np.concatenate(face_data2, axis=0)
    face_labels = np.concatenate(labels, axis=0).reshape((-1, 1))
    trainset = np.concatenate((face_dataset, face_labels), axis=1)
    return trainset, names


def recognize_faces(trainset, names):
    """
    基于训练集进行实时人脸识别并显示结果
    """
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_alt.xml")

    while True:
        ret, frame = cap.read()
        if ret == False:
            continue

        faces = face_cascade.detectMultiScale(frame, 1.3, 5)

        for face in faces:
            x, y, w, h = face

            offset = 10
            face_section = frame[y - offset:y + h + offset, x - offset:x + w + offset]
            face_section = cv2.resize(face_section, (100, 100))

            out = knn(trainset, face_section.flatten())
            pred_name = names[int(out)]
            cv2.putText(frame, pred_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

        cv2.imshow("Frame", frame)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return


if __name__ == "__main__":
    # 采集人脸数据
    collect_face_data()

    # 准备数据，获取训练集和人物名称映射
    trainset, names = prepare_data()

    # 进行人脸识别
    recognize_faces(trainset, names)