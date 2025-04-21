import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox, QLineEdit, QFileDialog
from PySide6.QtCore import Qt, QTimer  # 新增导入QTimer用于定时更新视频帧
from PySide6.QtTextToSpeech import QTextToSpeech
from PySide6.QtGui import QPixmap, QImage
from login import Ui_MainWindow
from function import Ui_FunctionWindow
from skimage.io import imread
from skimage.transform import resize
from joblib import dump, load
from mode import mode
from face import distance, knn, collect_face_data, prepare_data, recognize_faces
import cv2
trainset = None
names = None


class MyTestMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.button = QLabel("hello world", self)


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 创建的类和界面产生连接
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.speak = QTextToSpeech()

        self.ui.lineEdit_passwd.setStyleSheet("background:transparent;border-width:1;border-style:outset")
        self.ui.lineEdit_account.setStyleSheet("background:transparent;border-width:1;border-style:outset")

        self.ui.lineEdit_passwd.setEchoMode(QLineEdit.Password)

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(800, 600)  # 设置界面大小

        self.ui.pushButton_login.clicked.connect(self.login_func)
        self.ui.pushButton_register.clicked.connect(self.login_register)
        self.ui.pushButton.clicked.connect(self.login_face)

    def login_func(self):
        account = self.ui.lineEdit_account.text()
        passwd = self.ui.lineEdit_passwd.text()

        if account == "admin" and passwd == "admin":
            self.speak.say("登录成功")
            QMessageBox.information(self, "提示", "登录成功")
            # 当前的界面关闭
            self.close()
            # 定义一个功能界面
            self.functionWindow = FunctionWindow()
            # 功能界面显示
            self.functionWindow.show()

        else:
            self.speak.say("密码或账号不正确")
            QMessageBox.information(self, "警告", "密码或账户不正确")

            self.ui.lineEdit_passwd.setText("")
            self.ui.lineEdit_account.setText("")

    def login_register(self):
        """
        人脸注册功能，调用face.py中的函数来采集人脸数据并保存，然后更新训练集
        """
        # 先采集人脸数据并保存
        collect_face_data()

        # 重新准备数据，更新训练集和人物名称映射
        global trainset, names
        trainset, names = prepare_data()

        self.speak.say("注册成功，人脸信息已保存")
        QMessageBox.information(self, "提示", "注册成功，人脸信息已保存")

    def login_face(self):
        """
        人脸登录功能，通过比对人脸进行登录验证，调用face.py中的函数进行识别
        """
        if trainset is None or names is None:
            self.speak.say("请先注册人脸信息")
            QMessageBox.warning(self, "警告", "请先注册人脸信息")
            return

        # 采集当前要登录的人脸数据（这里简化处理，只获取一帧进行识别，可根据实际需求调整帧数等）
        cap = cv2.VideoCapture(0)
        face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_alt.xml")
        ret, frame = cap.read()
        if ret:
            grey_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(grey_frame, 1.3, 5)
            if len(faces) > 0:
                face = faces[0]  # 取第一个检测到的人脸，可根据情况调整处理多个脸的逻辑
                x, y, w, h = face

                offset = 10
                face_section = frame[y - offset:y + h + offset, x - offset:x + w + offset]
                face_section = cv2.resize(face_section, (100, 100))

                # 利用已有的训练集进行人脸识别
                out = knn(trainset, face_section.flatten())
                pred_name = names[int(out)]

                if pred_name:  # 简单判断是否识别到了已知人物，可根据实际情况完善验证逻辑
                    self.speak.say("登录成功")
                    QMessageBox.information(self, "提示", "人脸登录成功")
                    # 当前的界面关闭
                    self.close()
                    # 定义一个功能界面
                    self.functionWindow = FunctionWindow()
                    # 功能界面显示
                    self.functionWindow.show()
                else:
                    self.speak.say("人脸验证失败")
                    QMessageBox.warning(self, "警告", "人脸验证失败，请确认是否已注册")
            else:
                self.speak.say("未检测到人脸，请调整姿势后重试")
                QMessageBox.warning(self, "警告", "未检测到人脸，请调整姿势后重试")
        else:
            self.speak.say("摄像头获取图像失败，请检查摄像头是否正常")
            QMessageBox.warning(self, "警告", "摄像头获取图像失败，请检查摄像头是否正常")

        cap.release()


class FunctionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 创建的类和界面产生连接
        self.ui = Ui_FunctionWindow()
        self.ui.setupUi(self)
        # 创建语音模块
        self.speak = QTextToSpeech()
        # 创建一个照片路径
        self.filePath = ''
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(800, 600)

        # 关联退出按钮的信号和槽
        self.ui.pushButton_quit.clicked.connect(self.pushButton_quit_func)
        self.ui.pushButton_openpic.clicked.connect(self.pushButton_openPic_func)
        self.ui.pushButton_recognize.clicked.connect(self.pushButton_recognize_func)

        # 新增用于控制视频播放的定时器
        self.videoTimer = QTimer(self)
        self.videoTimer.timeout.connect(self.update_video_frame)

        # 用于存储当前打开的视频文件的VideoCapture对象
        self.videoCapture = None

    def pushButton_quit_func(self):
        self.close()
        self.login_Window = LoginWindow()
        self.login_Window.show()

    def pushButton_openPic_func(self):
        # 打开文件选择对话框，支持选择图片和视频
        file_path, _ = QFileDialog.getOpenFileName(self, "选择照片或视频", ".\image", "*.jpg;;*.png;;*.jpeg;;*.mp4;;*.avi")
        if file_path:
            self.filePath = file_path
            file_extension = file_path.split('.')[-1].lower()
            if file_extension in ["jpg", "png", "jpeg"]:
                # 如果是图片，按原逻辑显示
                pixmap = QPixmap(file_path)
                pixmap = pixmap.scaled(self.ui.label_Pic.size(), aspectMode=Qt.KeepAspectRatio)
                self.ui.label_Pic.setPixmap(pixmap)
            elif file_extension in ["mp4", "avi"]:
                # 如果是视频，初始化相关播放设置
                self.videoCapture = cv2.VideoCapture(file_path)
                if self.videoCapture.isOpened():
                    self.update_video_frame()  # 先显示第一帧
                    self.videoTimer.start(30)  # 设置定时器，每30毫秒更新一帧（帧率可调整）

    def update_video_frame(self):
        if self.videoCapture is None:
            return
        ret, frame = self.videoCapture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            im = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[2] * frame.shape[1],
                        QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(im).scaled(self.ui.label_Pic.size(), aspectMode=Qt.KeepAspectRatio)
            self.ui.label_Pic.setPixmap(pixmap)
        else:
            # 如果视频播放结束，重置相关状态
            self.videoCapture.release()
            self.videoTimer.stop()
            self.videoCapture = None

    def pushButton_recognize_func(self):
        if self.filePath == '':
            return

        bk_img = cv2.imread(self.filePath)

        img_array = imread(self.filePath)
        # 调整固定的大小(抗锯齿功能打开)
        img_resized = resize(img_array, (150, 150, 3), anti_aliasing=True)
        # 转成一维的
        flat_data = img_resized.flatten().reshape(1, -1)
        # 数据归一化
        flat_data = flat_data / 255.0
        # 加载对应模型
        loaded_mode = load(mode)
        # 调用模型进行预测
        prediction = loaded_mode.predict(flat_data)
        if prediction == 0:
            self.speak.say("苹果")
            self.ui.lineEdit_regongizeResult.setText("该图是苹果")
            cv2.putText(bk_img, "apple", (0, 5), cv2.FONT_HERSHEY_PLAIN, 0.2, (0, 0, 255), 1)
        else:
            self.speak.say("香蕉")
            self.ui.lineEdit_regongizeResult.setText("该图是香蕉")
            cv2.putText(bk_img, "banana", (0, 5), cv2.FONT_HERSHEY_PLAIN, 0.2, (0, 0, 255), 1)

        frame = cv2.cvtColor(bk_img, cv2.COLOR_BGR2RGB)
        im = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[2] * frame.shape[1], QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(im).scaled(self.ui.label_Pic.size(), aspectMode=Qt.KeepAspectRatio)
        self.ui.label_recognizePic.setPixmap(pixmap)


if __name__ == '__main__':
    print("main")
    app = QApplication(sys.argv)
    login_ui = LoginWindow()
    login_ui.show()
    app.exec()