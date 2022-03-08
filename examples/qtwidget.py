import sys
import pathlib
from pyglet import gl
import trimesh 
from trimesh.viewer.windowed import SceneViewerWidget
from PyQt5 import QtCore, QtOpenGL, Qt
here = pathlib.Path(__file__).resolve().parent

class ObjectSpace(object):
    """ Object space mocker """
    def __init__(self):
        # Textures and buffers scheduled for deletion the next time this
        # object space is active.
        self._doomed_textures = []
        self._doomed_buffers = []

class Context(object):
    """
    pyglet.gl.Context mocker. This is used to make pyglet believe that a valid
    context has already been setup. (Qt takes care of creating the open gl
    context)

    _Most of the methods are empty, there is just the minimum required to make
    it look like a duck..._
    """
    # define the same class attribute as pyglet.gl.Context
    CONTEXT_SHARE_NONE = None
    CONTEXT_SHARE_EXISTING = 1
    _gl_begin = False
    _info = None
    _workaround_checks = [
        ('_workaround_unpack_row_length',
         lambda info: info.get_renderer() == 'GDI Generic'),
        ('_workaround_vbo',
         lambda info: info.get_renderer().startswith('ATI Radeon X')),
        ('_workaround_vbo_finish',
         lambda info: ('ATI' in info.get_renderer() and
                       info.have_version(1, 5) and
                       sys.platform == 'darwin'))]
    _nscontext = None

    def __init__(self, context_share=None):
        """
        Setup workaround attr and object spaces (again to mock what is done in
        pyglet context)
        """
        self.object_space = ObjectSpace()
        for attr, check in self._workaround_checks:
            setattr(self, attr, None)

    def __repr__(self):
        return '%s()' % self.__class__.__name__

    def set_current(self):
        pass

    def destroy(self):
        pass

    def delete_texture(self, texture_id):
        pass

    def delete_buffer(self, buffer_id):
        pass

class QtViewerWidget(QtOpenGL.QGLWidget):
    """
    A simple widget for trimesh viewer.

    User can subclass this widget and implement the following methods:
        - on_init: called when open gl has been initialised
    """
    def __init__(self, model_path, parent=None, frame_time=32):
        """
        :param clear_color: The widget clear color
        :type clear_color: tuple(r, g, b, a)

        :param frame_time: The desired frame time [ms]
        :type: frame_time: int

        :param dt: The desired update rate [ms]
        :type: dt: int
        """
        QtOpenGL.QGLWidget.__init__(self, parent)

        # init members
        self.draw_timer = QtCore.QTimer()
        # configure draw and update timers
        self.draw_timer.setInterval(frame_time)
        self.draw_timer.timeout.connect(self.updateGL)
        # start timers
        self.draw_timer.start()
        self.model_path = model_path

    def initializeGL(self):
        """
        Initialises open gl:
            - create a mock context to fool pyglet
            - setup various opengl rule (only the clear color atm)
        """
        gl.current_context = Context()
        self.on_init()

    def on_init(self):
        """
        Lets the user initialise himself
        """
        self.w, self.h = 400, 300
        self.setMinimumSize(self.w, self.h)
        # self.setBaseSize(self.w, self.h)
        self.setSizePolicy(Qt.QSizePolicy.Expanding, Qt.QSizePolicy.Expanding)
        m = trimesh.load(self.model_path, process=False)
        scene = trimesh.Scene()
        scene.add_geometry(m)
        self.viewer = SceneViewerWidget(scene)
 
    def mousePressEvent(self, event):
        _buttons = 0
        if event.button() == QtCore.Qt.LeftButton:
            _buttons = 1
        elif event.button() == QtCore.Qt.RightButton:
            _buttons = 4
        elif event.button() == QtCore.Qt.MidButton:
            _buttons = 2
        _modifiers = 0
        if event.modifiers() & QtCore.Qt.ShiftModifier:
            _modifiers |= 1
        if event.modifiers() & QtCore.Qt.ControlModifier:
            _modifiers |= 2
        self.viewer.on_mouse_press(event.x(), event.y(), _buttons, _modifiers)

    def mouseMoveEvent(self, event) -> None:
        self.viewer.on_mouse_drag(event.x(), event.y())

    def wheelEvent(self, event) -> None:
        self.viewer.on_mouse_scroll(0, event.angleDelta().y() / 120)

    def resizeGL(self, w, h):
        self.viewer.on_resize(w, h)

    def paintGL(self):
        self.viewer.on_draw()

def main():
    app = Qt.QApplication(sys.argv)
    window = Qt.QMainWindow()
    widget = QtViewerWidget(str(here / '../models/fuze.obj'))
    window.setCentralWidget(widget)
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()