import copy

import cv2

from ._visual import _Visual


class MovingBar(_Visual):
    """
    Class to display a centered moving bar along the vertical or horizontal
    axis.

    Parameters
    ----------
    window_name : str
        Name of the window in which the visual is displayed.
    window_size : list | None
        Either None to automatically select a window size based on the
        available monitors, or a 2-length of positive integer sequence, as
        (width, height).
    """

    def __init__(self, window_name="Visual", window_size=None):
        super().__init__(window_name, window_size)
        self._backup_img = None

    def putBar(self, length, width, color, position=0, axis=0):
        """
        Backup the visual and draw the bar on top.

        Parameters
        ----------
        length : int
            Number of pixels used to draw the length of the bar.
        width : int
            Number of pixels used to draw the width of the bar.
        color : str | tuple
            Color used to fill the bar as a matplotlib string or a (B, G, R)
            tuple of int8 set between 0 and 255.
        position : int | float
            Relative position of the bar along the given axis.
            Along the vertical axis:
                - -1: corresponds to the top of the window.
                - 1: corresponds to the bottom of the window.
            Along the horizontal axis:
                - -1: corresponds to the left of the window.
                - 1: corresponds to the right of the window.
            0 corresponds to the center of the window.
        axis : int | str
            Axis along which the bar is moving:
                - 0 | 'vertical' | 'v'
                    horizontal bar along vertical axis.
                - 1 | 'horizontal' | 'h'
                    vertical bar along horizontal axis.
        """
        if self._backup_img is None:
            self._backup_img = copy.deepcopy(self._img)
        else:
            self._reset()

        self._position = MovingBar._check_position(position)
        self._axis = _Visual._check_axis(axis)

        self._length = MovingBar._check_length(
            length, self._axis, self.window_size
        )
        self._width = MovingBar._check_width(
            width, self._length, self._axis, self.window_size
        )
        self._color = _Visual._check_color(color)

        self._putBar()

    def _putBar(self):
        """
        Draw the bar rectangle.

        - Axis = 0 - Horizontal bar along vertical axis.
        P1 ---------------
        |                |
        --------------- P2

        - Axis = 1 - Vertical bar along horizontal axis
        P1 ---
        |    |
        |    |
        |    |
        |    |
        |    |
        --- P2
        """
        position = MovingBar._convert_position_to_pixel(
            self._position, self._axis, self.window_size, self.window_center
        )

        if self._axis == 0:
            xP1 = self.window_center[0] - self._length // 2
            yP1 = position - self._width // 2
            xP2 = xP1 + self._length
            yP2 = yP1 + self._width
        elif self._axis == 1:
            xP1 = position - self._width // 2
            yP1 = self.window_center[1] - self._length // 2
            xP2 = xP1 + self._width
            yP2 = yP1 + self._length

        cv2.rectangle(self._img, (xP1, yP1), (xP2, yP2), self._color, -1)

    def _reset(self):
        """
        Reset the visual with the backup, thus removing the bar.
        """
        self._img = copy.deepcopy(self._backup_img)

    # --------------------------------------------------------------------
    @staticmethod
    def _check_length(length, axis, window_size):
        """
        Checks that the length is strictly positive and shorter than the window
        dimension along the relevant axis.
        """
        length = int(length)
        assert 0 < length
        assert length <= window_size[axis]
        return length

    @staticmethod
    def _check_width(width, length, axis, window_size):
        """
        Checks that the width is strictly positive and shorter than the length,
        and shorter than the window dimension along the relevant axis.
        """
        width = int(width)
        assert 0 < width
        assert width <= length
        assert width <= window_size[(axis + 1) % 2]
        return width

    @staticmethod
    def _check_position(position):
        """
        Checks that the position given is between -1 and 1.
        """
        position = float(position)
        assert -1 <= position <= 1
        return position

    @staticmethod
    def _convert_position_to_pixel(position, axis, window_size, window_center):
        """
        Convert the relative position between -1 and 1 to an absolute position
        based on the window_size and window_center.
        """
        # horizontal bar moving up and down
        if axis == 0:
            if position == 0:
                return window_center[1]
            elif -1 <= position < 0:
                # top to center
                return int(window_center[1] * (1 - abs(position)))
            elif 0 < position <= 1:
                # center to bottom
                return int(
                    window_center[1]
                    + (window_size[1] - window_center[1]) * position
                )

        # vertical bar moving left and right
        elif axis == 1:
            if position == 0:
                return window_center[0]
            elif -1 <= position < 0:
                # left to center
                return int(window_center[0] * (1 - abs(position)))
            elif 0 < position <= 1:
                # center to right
                return int(
                    window_center[0]
                    + (window_size[0] - window_center[0]) * position
                )

    # --------------------------------------------------------------------
    @property
    def length(self):
        """
        Length of the bar in pixel.
        """
        return self._length

    @length.setter
    def length(self, length):
        self._length = MovingBar._check_length(
            length, self._axis, self.window_size
        )
        self._reset()
        self._putBar()

    @property
    def width(self):
        """
        Width of the bar in pixel.
        """
        return self._width

    @width.setter
    def width(self, width):
        self._width = MovingBar._check_width(
            width, self._length, self._axis, self.window_size
        )
        self._reset()
        self._putBar()

    @property
    def color(self):
        """
        Color of the bar.
        """
        return self._color

    @color.setter
    def color(self, color):
        self._color = _Visual._check_color(color)
        self._reset()
        self._putBar()

    @property
    def position(self):
        """
        Position between -1 and 1 of the bar on the given axis.
        """
        return self._position

    @position.setter
    def position(self, position):
        self._position = MovingBar._check_position(position)
        self._reset()
        self._putBar()

    @property
    def axis(self):
        """
        Axis on which the bar is moving.
            - 0: Horizontal bar along vertical axis.
            - 1: Vertical bar along horizonal axis.
        """
        return self._axis

    @axis.setter
    def axis(self, axis):
        self._axis = _Visual._check_axis(axis)
        self._reset()
        self._putBar()