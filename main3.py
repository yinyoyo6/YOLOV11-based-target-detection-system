import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox, QLineEdit, QFileDialog
from PySide6.QtCore import Qt, QTimer
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
import traceback
from ultralytics import YOLO

# 全局变量，用于存储训练集和人物名称映射，初始化为None
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

        # 设置密码输入框和账号输入框的样式，使其背景透明，有边框效果
        self.ui.lineEdit_passwd.setStyleSheet("background:transparent;border-width:1;border-style:outset")
        self.ui.lineEdit_account.setStyleSheet("background:transparent;border-width:1;border-style:outset")

        # 设置密码输入框的显示模式为密码模式（输入内容以密文显示）
        self.ui.lineEdit_passwd.setEchoMode(QLineEdit.Password)

        # 设置窗口无边框，并固定窗口大小为800x600
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(800, 600)

        # 连接登录按钮的点击信号到登录功能函数
        self.ui.pushButton_login.clicked.connect(self.login_func)
        # 连接注册按钮的点击信号到人脸注册功能函数
        self.ui.pushButton_register.clicked.connect(self.login_register)
        # 连接人脸登录按钮的点击信号到人脸登录功能函数
        self.ui.pushButton.clicked.connect(self.login_face)

    def login_func(self):
        """
        处理账号密码登录功能
        获取账号和密码输入框中的文本内容，与预设的账号密码（这里简单示例为"admin"）进行比对，
        根据比对结果给出相应提示信息，并进行相应界面操作（如登录成功则切换到功能界面）
        """
        account = self.ui.lineEdit_account.text()
        passwd = self.ui.lineEdit_passwd.text()

        if account == "admin" and passwd == "admin":
            self.speak.say("登录成功")
            QMessageBox.information(self, "提示", "登录成功")
            self.close()
            self.functionWindow = FunctionWindow()
            self.functionWindow.show()
        else:
            self.speak.say("密码或账号不正确")
            QMessageBox.information(self, "警告", "密码或账户不正确")
            self.ui.lineEdit_passwd.setText("")
            self.ui.lineEdit_account.setText("")

    def login_register(self):
        """
        人脸注册功能，调用face.py中的函数来采集人脸数据并保存，然后更新训练集
        如果过程中出现异常，会弹出相应的错误提示信息
        """
        try:
            # 先采集人脸数据并保存
            collect_face_data()

            # 重新准备数据，更新训练集和人物名称映射
            global trainset, names
            trainset, names = prepare_data()

            self.speak.say("注册成功，人脸信息已保存")
            QMessageBox.information(self, "提示", "注册成功，人脸信息已 saved")
        except Exception as e:
            error_msg = f"人脸注册出现错误: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)

    def login_face(self):
        """
        人脸登录功能，通过比对人脸进行登录验证，调用face.py中的函数进行识别
        如果训练集或人物名称映射为空，提示先注册人脸信息；
        如果人脸比对过程出现其他异常，也会弹出相应错误提示信息
        """
        if trainset is None or names is None:
            self.speak.say("请先注册人脸信息")
            QMessageBox.warning(self, "警告", "请先注册人脸信息")
            return

        try:
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
                        self.close()
                        self.functionWindow = FunctionWindow()
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
        except Exception as e:
            error_msg = f"人脸登录出现错误: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)


class FunctionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 创建的类和界面产生连接
        self.ui = Ui_FunctionWindow()
        self.ui.setupUi(self)
        self.speak = QTextToSpeech()
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

        # 加载YOLO模型
        self.model = YOLO("yolo11n-pose.onnx")

    def pushButton_quit_func(self):
        """
        处理退出按钮点击事件，关闭当前功能界面，显示登录界面
        """
        self.close()
        self.login_Window = LoginWindow()
        self.login_Window.show()

    def pushButton_openPic_func(self):
        """
        处理打开图片或视频文件的功能
        通过文件对话框让用户选择图片或视频文件，根据文件类型进行相应的显示处理，
        对于视频文件，初始化播放相关设置（显示第一帧并启动定时器定时更新帧）
        如果文件选择或打开过程出现异常，弹出相应错误提示信息
        """
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择照片或视频", ".\image",
                                                      "*.jpg;;*.png;;*.jpeg;;*.mp4;;*.avi")
            if file_path:
                self.filePath = file_path
                file_extension = file_path.split('.')[-1].lower()
                if file_extension in ["jpg", "png", "jpeg"]:
                    self.display_image(file_path)
                elif file_extension in ["mp4", "avi"]:
                    self.videoCapture = cv2.VideoCapture(file_path)
                    if self.videoCapture.isOpened():
                        self.update_video_frame()  # 先显示第一帧
                        self.videoTimer.start(30)  # 设置定时器，每30毫秒更新一帧（帧率可调整）
                    else:
                        raise ValueError("无法打开视频文件")
        except Exception as e:
            error_msg = f"打开文件出现错误: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)

    def update_video_frame(self):
        """
        用于定时更新视频播放的帧画面
        如果视频读取正常，将读取到的帧转换为适合Qt显示的格式并显示在相应的Label上；
        如果视频播放结束，重置相关播放状态（释放资源、停止定时器等）
        """
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
            self.videoCapture.release()
            self.videoTimer.stop()
            self.videoCapture = None

    def display_image(self, file_path):
        """
        辅助函数，用于将给定路径的图片显示在相应的Label上
        """
        pixmap = QPixmap(file_path)
        pixmap = pixmap.scaled(self.ui.label_Pic.size(), aspectMode=Qt.KeepAspectRatio)
        self.ui.label_Pic.setPixmap(pixmap)

    def pushButton_recognize_func(self):
        """
        处理识别按钮点击事件，根据选择的文件（图片或视频）进行相应的识别操作
        如果是图片，进行简单的分类识别（原逻辑，可根据实际情况完善模型及识别逻辑）并展示结果；
        如果是视频，调用yolo11n-pose.onnx模型进行目标检测等操作，并展示结果，
        如果文件读取或识别过程出现异常，弹出相应错误提示信息
        """
        if self.filePath == '':
            return

        try:
            file_extension = self.filePath.split('.')[-1].lower()
            if file_extension in ["jpg", "png", "jpeg"]:
                self.recognize_image()
            elif file_extension in ["mp4", "avi"]:
                self.recognize_video()
        except Exception as e:
            error_msg = f"识别出现错误: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "错误", error_msg)

    def recognize_image(self):
        """
        针对图片文件进行识别的具体逻辑，原逻辑基础上可根据实际情况完善模型及后续处理
        """
        img_array = imread(self.filePath)
        img_resized = resize(img_array, (150, 150, 3), anti_aliasing=True)
        flat_data = img_resized.flatten().reshape(1, -1)
        flat_data = flat_data / 255.0
        loaded_mode = load(mode)
        prediction = loaded_mode.predict(flat_data)
        if prediction == 0:
            self.speak.say("苹果")
            self.ui.lineEdit_regongizeResult.setText("该图是苹果")
            self.draw_result_text("apple")
        else:
            self.speak.say("香蕉")
            self.ui.lineEdit_regongizeResult.setText("该图是香蕉")
            self.draw_result_text("banana")

    def recognize_video(self):
        """
        针对视频文件进行识别的具体逻辑，调用yolo11n-pose.onnx模型进行目标检测，
        并将检测结果展示在自定义的UI界面相关控件上（这里是self.ui.label_recognizePic），
        不再弹出额外的显示结果窗口
        """
        cap = cv2.VideoCapture(self.filePath)
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                result = self.model(frame)  # 对每一帧进行检测，这里不再使用track及show=True参数
                boxes = result[0].boxes
                for box in boxes:
                    class_id = box.cls.cpu().numpy()[0]
                    class_name = self.model.names[int(class_id)]
                    self.speak.say(class_name)
                    self.ui.lineEdit_regongizeResult.setText(f"检测到目标: {class_name}")
                    # 可以进一步获取坐标等信息绘制到画面上展示（以下坐标获取是示例，按实际调整）
                    x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0].astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                im = QImage(frame.data, frame.shape[1], frame.shape[0], frame.shape[2] * frame.shape[1],
                            QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(im).scaled(self.ui.label_recognizePic.size(),
                                                     aspectMode=Qt.KeepAspectRatio)
                self.ui.label_recognizePic.setPixmap(pixmap)
            else:
                break
        cap.release()

    def draw_result_text(self, text, frame=None):
        """
        辅助函数，用于在给定的图像（如果有）上绘制识别结果文本
        """
        if frame is None:
            frame = cv2.imread(self.filePath)
        cv2.putText(frame, text, (0, 5), cv2.FONT_HERSHEY_PLAIN, 0.2, (0, 0, 255), 1)


if __name__ == '__main__':
    print("main")
    app = QApplication(sys.argv)
    login_ui = LoginWindow()
    login_ui.show()
    app.exec()