import os
import threading
from typing import Dict, List, Any, Callable, Optional, Union
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import pygame.gfxdraw
import string
import math
import functools
import date_kit
from date_kit import Date
import webbrowser
import toolkit
import copy
import time

CENTER = 0
TOPLEFT = 1
RIGHT = 2
TOP = 3
BOTTOM = 4
TOPRIGHT = 5
BOTTOMLEFT = 6
LEFT = 7
BOTTOMRIGHT = 8

NORMAL_STATE = 0
HIGHLIGHT_STATE = 1
PRESS_STATE = 2
SELECT_STATE = 3
DISABLE_STATE = 4

black = (0, 0, 0)
white = (255, 255, 255)
grey = (200, 200, 200)
light_grey = (220, 220, 220)
dark_grey = (180, 180, 180)
whitish = (250, 250, 250)
gold = (212, 175, 55)
green = (20, 200, 20)
red = (255, 80, 80)
yellow = (255, 255, 0)
colour_ratio = 1.15
faded_text = 150

widgets = []
faded_colours = {}
text_capture = []

os.environ['SDL_VIDEO_WINDOW_POS'] = '1'
pygame.init()
monitor_info = pygame.display.Info()
screen_width = int(monitor_info.current_w)
screen_height = int(monitor_info.current_h)
screen_dimensions = (screen_width, screen_height)
screen_dimension_ratio = screen_width / screen_height
screen_center = (screen_width / 2, screen_height / 2)
screen_rect = pygame.Rect((0, 0), screen_dimensions)

screen = pygame.display.set_mode(screen_dimensions, pygame.NOFRAME)
clock = pygame.time.Clock()

BUTTON_SCROLL = 3
SLIDER_SPEED = 1
SCROLL_SPEED = 5
SCROLL_SENSITIVITY = int(screen_height / 64)
SCROLL_RESISTANCE = 0.92
DEFAULT_EDGE = int(screen_width / 128)
FONT_ASPECT = 0.42
TOOLTIP_OFFSET = int(screen_width / 64)
BASE_FONT_SIZE = int(screen_width / 96)
TITLE_SIZE = BASE_FONT_SIZE * 2
SHADOW = round(screen_height / 432) + 1
DEFAULT_FONT = 'mongolianbaiti'


class Widget:
    change = False
    alpha_rate = 5
    cursor_type = 0
    new_cursor_type = 0

    def __init__(self, position, area, align=TOPLEFT, surface=None, default_alpha=255, appearing=False, parent=None,
                 catchable=True, no_catch=False):
        self.parent = parent
        if surface is None:
            self.surface = pygame.Surface(area)
        else:
            self.surface = surface
        self.default_alpha = default_alpha
        self.fading = appearing
        self.appearing = appearing
        self.catchable = catchable
        self.no_catch = no_catch
        self.disappearing = False
        self.rect = self.surface.get_rect()
        self.alignment = align
        self.align(align, position)
        self.contain_rect = self.rect.copy()
        self._tooltip = None
        self.tooltip_display = None
        self.components = []
        self.extensions = []
        self.transparency()
        Widget.change = True

    def align(self, align, position):
        if align == CENTER:
            self.rect.center = position
        elif align == TOPLEFT:
            self.rect.topleft = position
        elif align == RIGHT:
            self.rect.midright = position
        elif align == TOP:
            self.rect.midtop = position
        elif align == BOTTOM:
            self.rect.midbottom = position
        elif align == TOPRIGHT:
            self.rect.topright = position
        elif align == BOTTOMLEFT:
            self.rect.bottomleft = position
        elif align == LEFT:
            self.rect.midleft = position
        elif align == BOTTOMRIGHT:
            self.rect.bottomright = position

    def handle(self, event, mouse):
        if self.in_container(mouse):
            for c in self.components:
                c.handle(event, mouse)
        for e in self.components:
            e.handle(event, mouse)
        return False

    def catch(self, mouse):
        if not self.no_catch:
            if self.in_container(mouse):
                for i in range(len(self.components)):
                    if self.components[-(i + 1)].catch(mouse):
                        return True
            for i in range(len(self.extensions)):
                if self.extensions[-(i + 1)].catch(mouse):
                    return True
            if self.catchable and self.on_top(mouse):
                if self.tooltip_display is None:
                    self.tooltip_display = self.make_tooltip(mouse)
                    if self.tooltip_display is not None:
                        self.tooltip_display.show()
                else:
                    self.tooltip_display.update(mouse)
                defocus_button()
                return True
        return False

    def no_focus(self):
        for c in self.components:
            c.no_focus()
        for e in self.extensions:
            e.no_focus()

    def get_surface(self):
        return self.surface

    def display(self, container=screen_rect):
        contain = self.contain_rect
        seen = True
        surface = self.get_surface()
        if container is screen_rect or container.contains(self.rect):
            screen.blit(surface, self.rect)
        elif container.colliderect(self.rect):
            visible = pygame.Rect((0, 0), (self.rect.w, self.rect.h))
            temp = self.rect.copy()
            if self.rect.bottom > container.bottom:
                visible.h = container.bottom - self.rect.top
            if self.rect.top < container.top:
                temp.h = temp.bottom - container.top - (self.rect.height - visible.height)
                temp.bottom = self.rect.bottom - (self.rect.height - visible.height)
                visible.h = temp.h
                visible.top = container.top - self.rect.top
            if self.rect.right > container.right:
                visible.width = container.right - self.rect.left
            if self.rect.left < container.left:
                temp.width = temp.right - container.left - (self.rect.width - visible.width)
                temp.right = self.rect.right - (self.rect.width - visible.width)
                visible.width = temp.width
                visible.left = container.left - self.rect.left
            screen.blit(surface, temp, visible)
            contain = pygame.Rect(temp.topleft, visible.size)
        else:
            seen = False
        actual = self.actual_container()
        if actual is not None:
            for e in self.extensions:
                e.display(actual)
        if seen:
            for c in self.components:
                c.display(contain)

    def actual_container(self, container=screen_rect):
        if self.parent is not None:
            try:
                limit = self.parent.contain_rect
            except AttributeError:
                return container
            if self in self.parent.extensions or limit.contains(container):
                return self.parent.actual_container(container)
            elif container.contains(limit) or container.colliderect(limit):
                if limit.bottom < container.bottom:
                    bottom = limit.bottom
                else:
                    bottom = container.bottom
                if limit.top > container.top:
                    top = limit.top
                else:
                    top = container.top
                if limit.right < container.right:
                    right = limit.right
                else:
                    right = container.right
                if limit.left > container.left:
                    left = limit.left
                else:
                    left = container.left
                return self.parent.actual_container(pygame.Rect((left, top), (right - left, bottom - top)))
            else:
                return None
        else:
            return container

    def animate(self):
        alpha_ratio = self.alpha_rate / self.default_alpha
        if self.appearing:
            self.appear(alpha_ratio)
        elif self.disappearing:
            self.disappear(alpha_ratio)
        for c in self.components + self.extensions:
            c.animate()

    def appear(self, alpha_ratio, first=True):
        Widget.change = True
        alpha_rate = alpha_ratio * self.default_alpha
        if first and self.default_alpha - self.surface.get_alpha() <= alpha_rate:
            self.change_alpha(self.default_alpha)
            for c in self.components + self.extensions:
                c.surface.set_alpha(c.default_alpha)
            self.appearing = False
        else:
            self.change_alpha(self.surface.get_alpha() + alpha_rate)
            for c in self.components + self.extensions:
                c.appear(alpha_ratio, first=False)

    def disappear(self, alpha_ratio, first=True):
        Widget.change = True
        alpha_rate = alpha_ratio * self.default_alpha
        if first and self.surface.get_alpha() - alpha_rate <= 0:
            self.hide()
            del self
            return
        else:
            if self.surface.get_alpha() is not None:
                self.surface.set_alpha(self.surface.get_alpha() - alpha_rate)
                for c in self.components + self.extensions:
                    c.disappear(alpha_ratio, first=False)
            else:
                self.hide()
                del self
                return

    def change_alpha(self, alpha):
        self.surface.set_alpha(alpha)

    def transparency(self):
        if self.appearing:
            self.transparent()
        else:
            self.surface.set_alpha(self.default_alpha)

    def transparent(self):
        self.surface.set_alpha(0)
        for c in self.components + self.extensions:
            c.transparent()

    def appeared(self):
        self.surface.set_alpha(self.default_alpha)
        for c in self.components + self.extensions:
            c.appeared()

    def on_top(self, pos):
        if self.rect.left <= pos[0] <= self.rect.right and self.rect.top <= pos[1] <= self.rect.bottom:
            return True
        else:
            return False

    def in_container(self, pos):
        if self.contain_rect.left <= pos[0] <= self.contain_rect.right and \
                self.contain_rect.top <= pos[1] <= self.contain_rect.bottom:
            return True
        else:
            return False

    def draw_borders(self, thickness=1, color=black):
        pygame.draw.rect(self.surface, color, (0, 0, thickness, self.rect.h))
        pygame.draw.rect(self.surface, color, (self.rect.w - thickness, 0, thickness, self.rect.h))
        pygame.draw.rect(self.surface, color, (0, 0, self.rect.w, thickness))
        pygame.draw.rect(self.surface, color, (0, self.rect.h - thickness, self.rect.w, thickness))

    def scroll(self, velocity):
        if velocity != 0:
            Widget.change = True
            for c in self.components:
                c.rect.y -= velocity
                c.contain_rect.y -= velocity
                c.scroll(velocity)

    def show(self):
        widgets.append(self)
        self.transparency()
        Widget.change = True

    def hide(self):
        try:
            widgets.remove(self)
            Widget.change = True
        except ValueError:
            pass

    def move_to(self, pos, align=None):
        orig_pos = self.rect.topleft
        rel_pos = []
        dif: List[int] = [self.contain_rect.left - self.rect.left, self.contain_rect.top - self.rect.top]
        for component in self.components + self.extensions:
            rel_pos.append([component.rect.left - self.rect.left, component.rect.top - self.rect.top])
        if align is None:
            align = self.alignment
        self.align(align, pos)
        if self.rect.topleft != orig_pos:
            self.contain_rect.left = self.rect.left + dif[0]
            self.contain_rect.top = self.rect.top + dif[1]
            for i, component in enumerate(self.components + self.extensions):
                component.move_to([pos[0] + rel_pos[i][0], pos[1] + rel_pos[i][1]], align)
            Widget.change = True

    def move(self, x=0, y=0):
        if x != 0 or y != 0:
            self.rect.x += x
            self.rect.y += y
            self.contain_rect.x += x
            self.contain_rect.y += y
            for c in self.components:
                c.move(x, y)
            for e in self.extensions:
                e.move(x, y)
            Widget.change = True

    def set_tooltip(self, tip=None):
        self._tooltip = tip

    def make_tooltip(self, mouse):
        if self._tooltip is None:
            return None
        elif type(self._tooltip).__name__ == 'str':
            return ToolTip(self._tooltip, (mouse[0], mouse[1] + TOOLTIP_OFFSET))
        else:
            return self._tooltip

    def get_width(self):
        return self.rect.w

    def get_height(self):
        return self.rect.h


class Button(Widget):
    buttons = []
    default_height = int(screen_height / 14)
    default_width = int(screen_width / 9)
    focus = None

    def __init__(self, position, area=None, align=TOPLEFT, label=None, label_size=BASE_FONT_SIZE, parent=None,
                 border_thickness=1, border_colour=black, colour=grey, threed=True, visible=True):
        if area is None:
            area = (self.default_width, self.default_height)
        self.surface = pygame.Surface(area)
        super().__init__(position, area, align, self.surface, parent=parent)
        if border_thickness == 0:
            self.borders = False
        else:
            self.borders = True
        self.border_thickness = border_thickness
        self.border_colour = border_colour

        self.state = NORMAL_STATE

        self.colours = []
        self.normal_colour = colour
        self.press_colour = None
        self.highlight_colour = None
        self.visible = visible

        self.current_label = None
        self.label_size = label_size
        if label is not None:
            self.label(label)
        self.threed = threed
        self.pressed = False
        if self.threed:
            self.shadow = Widget(self.rect.bottomleft, (self.rect.w, SHADOW))
            self.shadow.surface.fill(black)
            self.shadow.surface.set_alpha(200)
            self.extensions.append(self.shadow)

        self.funcs = []

        self.sheet = Widget(self.rect.topleft, self.rect.size, parent=self, default_alpha=150, catchable=False)
        self.sheet.surface.fill(grey)

        self.update()
        Button.buttons.append(self)

    def handle(self, event, mouse):
        state = self.state
        if self.on_top(mouse):
            if self.state is not DISABLE_STATE:
                for c in self.components:
                    if c.handle(event, mouse):
                        break
                else:
                    if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed(3)[0]:
                        self.state = PRESS_STATE
                    elif event.type == pygame.MOUSEBUTTONUP and self.state is PRESS_STATE and \
                            not pygame.mouse.get_pressed(3)[0]:
                        self.state = HIGHLIGHT_STATE
                        self.call_funcs()
                    if state != self.state:
                        self.update()
            return True
        else:
            return False

    def call_funcs(self):
        for func in self.funcs:
            func()

    def callback(self, func, returns=False):
        if returns:
            self.funcs.append(functools.partial(func, self))
        else:
            self.funcs.append(func)

    def reset_callbacks(self):
        self.funcs.clear()

    def catch(self, mouse):
        if self.on_top(mouse):
            for c in self.components:
                if c.catch(mouse):
                    break
            else:
                if not self.visible:
                    Widget.new_cursor_type = 1
                if self.tooltip_display is None:
                    self.tooltip_display = self.make_tooltip(mouse)
                    if self.tooltip_display is not None:
                        self.tooltip_display.show()
                else:
                    self.tooltip_display.update(mouse)
                if self.state is NORMAL_STATE:
                    self.state = HIGHLIGHT_STATE
                    self.update()
                if Button.focus is not None and Button.focus is not self:
                    Button.focus.no_focus()
                Button.focus = self
            return True
        else:
            return False

    def no_focus(self):
        if self.state in [HIGHLIGHT_STATE, PRESS_STATE]:
            self.state = NORMAL_STATE
            self.update()
        if self.tooltip_display is not None:
            self.tooltip_display.hide()
            self.tooltip_display = None
        if Button.focus is self:
            Button.focus = None

    def update(self):
        if self.visible:
            self.update_colours()

            if self.state is DISABLE_STATE:
                self.surface.fill(self.colours[NORMAL_STATE])
            else:
                self.surface.fill(self.colours[self.state])

            if self.state in [PRESS_STATE, SELECT_STATE, DISABLE_STATE] and not self.pressed and self.threed:
                self.move(y=SHADOW)
                self.pressed = True
                self.extensions.remove(self.shadow)
            elif self.state not in [PRESS_STATE, SELECT_STATE] and self.pressed and self.threed:
                self.move(y=-SHADOW)
                self.pressed = False
                self.shadow.rect.topleft = self.rect.bottomleft
                self.extensions.append(self.shadow)

            if self.borders:
                self.draw_borders(self.border_thickness)

            if self.tooltip_display is not None and not self.on_top(pygame.mouse.get_pos()):
                self.tooltip_display.hide()
                self.tooltip_display = None
        else:
            self.surface.fill(white)
            self.surface.set_colorkey(white)

        Widget.change = True

    def disable(self):
        if self.state is not DISABLE_STATE:
            self.state = DISABLE_STATE
            self.update()
            self.sheet.rect.topleft = self.rect.topleft
            self.components.append(self.sheet)

    def enable(self):
        if self.state is DISABLE_STATE:
            self.state = NORMAL_STATE
            self.update()
            self.components.remove(self.sheet)

    def update_colours(self):
        self.highlight_colour = tuple(map(set_highlight_colour, self.normal_colour))
        self.press_colour = tuple(map(set_press_colour, self.normal_colour))
        self.colours = [self.normal_colour, self.highlight_colour, self.press_colour, self.highlight_colour]

    def label(self, text, size=None, colour=None):
        if size is None:
            size = self.label_size
        else:
            self.label_size = size
        if colour is None:
            colour = black
        if self.current_label is not None:
            self.components.remove(self.current_label)
        self.current_label = Text(text, self.rect.center, font_size=size, colour=colour,
                                  background_colour=self.normal_colour)
        self.components.append(self.current_label)

    def draw_borders(self, thickness=1, color=None):
        if color is None:
            color = self.border_colour
        pygame.draw.rect(self.surface, color, (0, 0, thickness, self.rect.h))
        pygame.draw.rect(self.surface, color, (self.rect.w - thickness, 0, thickness, self.rect.h))
        pygame.draw.rect(self.surface, color, (0, 0, self.rect.w, thickness))
        if not self.threed or self.pressed:
            pygame.draw.rect(self.surface, color, (0, self.rect.h - thickness, self.rect.w, thickness))

    def expand(self):
        self.parent.expand(self)

    def scroll(self, velocity):
        if velocity != 0:
            for c in self.extensions:
                c.rect.y -= velocity
                c.contain_rect.y -= velocity
                c.scroll(velocity)
        super().scroll(velocity)

    def hide(self):
        if self.tooltip_display in BaseToolTip.instances:
            self.tooltip_display.hide()
            self.tooltip_display = None
        super().hide()


def defocus_button():
    if Button.focus is not None:
        Button.focus.no_focus()
        Button.focus = None
    Widget.new_cursor_type = 0


class CircleButton(Button):

    def __init__(self, position, radius, align=CENTER, parent=None,
                 border_thickness=2, border_colour=black, colour=grey, **kwargs):
        self.radius = radius
        if "threed" in kwargs:
            kwargs.pop("threed")
        if "area" in kwargs:
            kwargs.pop("area")
        super().__init__(position, area=(radius * 2, radius * 2), align=align, parent=parent, colour=colour,
                         border_thickness=border_thickness, border_colour=border_colour, threed=False, **kwargs)

    def on_top(self, pos):
        if ((pos[0] - self.rect.centerx) ** 2 + (pos[1] - self.rect.centery) ** 2) ** (1 / 2) < self.radius:
            return True
        else:
            return False

    def update(self):
        self.update_colours()
        self.surface.fill(white)
        r = self.radius - 1
        if self.state is SELECT_STATE:
            pygame.gfxdraw.aacircle(self.surface, r, r, r, gold)
            pygame.gfxdraw.filled_circle(self.surface, r, r, r, gold)
            pygame.gfxdraw.aacircle(self.surface, r, r, r - 2, self.colours[self.state])
            pygame.gfxdraw.filled_circle(self.surface, r, r, r - 2, self.colours[self.state])
        else:
            if self.border_thickness > 0:
                pygame.gfxdraw.aacircle(self.surface, r, r, r, self.border_colour)
                pygame.gfxdraw.filled_circle(self.surface, r, r, r, self.border_colour)
            pygame.gfxdraw.filled_circle(self.surface, r, r, r - self.border_thickness, self.colours[self.state])
            pygame.gfxdraw.aacircle(self.surface, r, r, r - self.border_thickness, self.colours[self.state])
        if self.tooltip_display is not None and not self.on_top(pygame.mouse.get_pos()):
            self.tooltip_display.hide()
            self.tooltip_display = None
        Widget.change = True


class SelectButton(Button):

    def __init__(self, position, area, align=TOPLEFT, label=None, label_size=BASE_FONT_SIZE,
                 parent=None, border_thickness=1, border_colour=black, colour=grey,
                 threed=True, deselectable=True, select_thic=2, exclusive=True, **kwargs):
        super().__init__(position, area, align=align, label=label, label_size=label_size,
                         parent=parent, border_thickness=border_thickness, border_colour=border_colour,
                         colour=colour, threed=threed, **kwargs)
        self.deselectable = deselectable
        self.select_thic = select_thic
        self.exclusive = exclusive
        if self.deselectable:
            self.release_funcs = {}

    def handle(self, event, mouse):
        if self.on_top(mouse):
            if self.state is not DISABLE_STATE:
                for c in self.components:
                    if c.handle(event, mouse):
                        break
                else:
                    if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed(3)[0]:
                        if self.state is not SELECT_STATE:
                            self.select()
                            self.call_funcs()
                        elif self.deselectable:
                            self.state = HIGHLIGHT_STATE
                            self.update()
                            self.call_release_funcs()
            return True
        else:
            return False

    def update(self):
        super().update()
        if self.state == SELECT_STATE:
            self.draw_borders(thickness=self.select_thic, color=gold)

    def release_callback(self, func, returns=False):
        self.release_funcs[func] = returns

    def call_release_funcs(self):
        for func in self.release_funcs:
            if self.release_funcs[func]:
                func(self)
            else:
                func()

    def select(self):
        if self.parent is not None and self.exclusive:
            for comp in self.parent.select_buttons:
                if comp is not self and comp.state is not DISABLE_STATE:
                    comp.state = NORMAL_STATE
                    comp.update()
        self.state = SELECT_STATE
        self.update()


class CircleSelectButton(CircleButton, SelectButton):

    def __init__(self, position, radius, parent=None, align=CENTER, **kwargs):
        self.radius = radius
        if "area" not in kwargs:
            kwargs["area"] = (radius * 2, radius * 2)
        super().__init__(position, radius=radius, parent=parent, align=align, **kwargs)


class ScrollBar(Widget):
    img = os.path.dirname(__file__) + '/play.png'

    def __init__(self, position, area, parent, align=TOPLEFT):
        super().__init__(position, area, align=align, parent=parent)
        self.surface.fill((230, 230, 230))
        self.marg = self.rect.w
        c_range = self.rect.h - 2 * self.marg
        self.scale = c_range / self.parent.total_size
        cursor_height = round(self.scale * self.parent.contain_rect.h)
        min_height = int(screen_height / 48)
        if cursor_height < min_height:
            self.scale = self.scale * (c_range - min_height) / (c_range - cursor_height)
            cursor_height = min_height
        self.cursor = ScrollCursor((self.rect.x, self.rect.y + self.marg), (self.rect.w, cursor_height),
                                   parent=self)
        self.components.append(self.cursor)

        top = Button(self.rect.topleft, (self.marg, self.marg), align=TOPLEFT, threed=False)
        img = Image(top.rect.center, (top.rect.w, top.rect.h), Slider.img)
        img.surface = pygame.transform.rotate(img.surface, 90)
        top.components.append(img)
        self.top_b = top
        self.components.append(self.top_b)

        bottom = Button(self.rect.bottomleft, (self.marg, self.marg), align=BOTTOMLEFT, threed=False)
        img = Image(bottom.rect.center, (bottom.rect.w, bottom.rect.h), Slider.img)
        img.surface = pygame.transform.rotate(img.surface, 270)
        bottom.components.append(img)
        self.bottom_b = bottom
        self.components.append(self.bottom_b)

    def handle(self, event, mouse):
        if self.on_top(mouse):
            for c in self.components:
                if c.handle(event, mouse):
                    break
            return True
        return False

    def animate(self):
        if self.bottom_b.state is PRESS_STATE:
            self.cursor.animate(BUTTON_SCROLL)
        elif self.top_b.state is PRESS_STATE:
            self.cursor.animate(-BUTTON_SCROLL)
        super().animate()


class ScrollCursor(Button):

    def __init__(self, position, area, align=TOPLEFT, parent=None, border_thickness=0):
        super().__init__(position, area, align, parent=parent, border_thickness=border_thickness,
                         threed=False)
        self.y_loc = None
        self.subject = self.parent.parent
        self.loc = 0
        self.normal_colour = dark_grey
        self.update()

    def update_colours(self):
        self.highlight_colour = tuple(map(set_press_colour, self.normal_colour))
        self.press_colour = tuple(map(set_press_colour, self.highlight_colour))
        self.colours = [self.normal_colour, self.highlight_colour, self.press_colour, self.highlight_colour]

    def handle(self, event, mouse):
        state = self.state
        if self.on_top(mouse):
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed(3)[0] and \
                    self.state is not PRESS_STATE:
                self.state = PRESS_STATE
                self.y_loc = mouse[1]
            elif event.type == pygame.MOUSEBUTTONUP and self.state is PRESS_STATE and \
                    not pygame.mouse.get_pressed(3)[0]:
                self.state = HIGHLIGHT_STATE
            if self.state is NORMAL_STATE:
                self.state = HIGHLIGHT_STATE
            if state != self.state:
                self.update()
            return True
        else:
            if self.state not in [PRESS_STATE, NORMAL_STATE]:
                self.state = NORMAL_STATE
            self.update()
            return False

    def animate(self, move=0):
        mouse = pygame.mouse.get_pos()
        if self.y_loc is not None and self.state is PRESS_STATE:
            if not pygame.mouse.get_pressed(3)[0]:
                self.state = NORMAL_STATE
                self.update()
            amount = (mouse[1] - self.y_loc) / (self.parent.rect.h - 2 * self.parent.marg - self.rect.h) * \
                     (self.subject.total_size - self.subject.contain_rect.h)
            if (amount > 0 and mouse[1] > self.parent.rect.top + self.parent.rect.w) or \
                    (amount < 0 and mouse[1] < self.parent.rect.bottom - self.parent.rect.w):
                move += amount
            self.subject.scrolling(move)
            self.y_loc = mouse[1]
        elif move != 0:
            self.subject.scrolling(move)
        should = round(self.parent.rect.top + self.parent.scale * self.subject.scroll_pos + self.parent.marg)
        if self.rect.y != should:
            self.rect.y = should
            Widget.change = True
        super().animate()

    def no_focus(self):
        if self.state is HIGHLIGHT_STATE:
            self.state = NORMAL_STATE
            self.update()


class Slider(Widget):
    img = os.path.dirname(__file__) + '/play.png'

    def __init__(self, pos, area, effect, point, align=CENTER, parent=None, minimum=0, maximum=1, log=False,
                 shape='rect'):
        super().__init__(pos, area, align=align, parent=parent)
        self.surface.fill((230, 230, 230))
        self.effect = effect
        self.log = log
        if self.log:
            self.min = math.log10(minimum)
            self.max = math.log10(maximum)
            self.point = math.log10(point)
        else:
            self.min = minimum
            self.max = maximum
            self.point = point
        r = int(self.rect.h / 2)
        self.slider = SliderButton((0, self.rect.centery), (r, 2 * r), parent=self, shape=shape)
        self.set_value(point)
        self.components.append(self.slider)

        right = Button(self.rect.topright, (self.rect.h, self.rect.h), align=TOPRIGHT, threed=False)
        img = Image(right.rect.center, right.rect.size, Slider.img)
        right.components.append(img)
        self.right_b = right
        self.components.append(self.right_b)

        left = Button(self.rect.topleft, (self.rect.h, self.rect.h), align=TOPLEFT, threed=False)
        img = Image(left.rect.center, left.rect.size, Slider.img)
        img.surface = pygame.transform.flip(img.surface, True, False)
        left.components.append(img)
        self.left_b = left
        self.components.append(self.left_b)

    def get_value(self):
        v = ((self.slider.loc - self.slider.min) / (self.slider.max - self.slider.min)
             * (self.max - self.min) + self.min)
        if self.log:
            v = 10 ** v
        return v

    def set_value(self, v):
        if self.log:
            v = math.log10(v)
        slider_loc = (v - self.min) / (self.max - self.min) * (self.slider.max - self.slider.min) + self.slider.min
        self.slider.set_loc(slider_loc)

    def handle(self, event, mouse):
        if self.on_top(mouse):
            for c in self.components:
                if c.handle(event, mouse):
                    break
            return True
        return False

    def animate(self):
        if self.left_b.state is PRESS_STATE:
            self.slider.animate(-SLIDER_SPEED)
        elif self.right_b.state is PRESS_STATE:
            self.slider.animate(SLIDER_SPEED)
        super().animate()


class SliderButton(Button):

    def __init__(self, pos, dim, parent, align=CENTER, shape='rect', col=gold):
        self.shape = shape
        if self.shape == 'circ':
            self.radius = dim[0]
            area = (self.radius * 2, self.radius * 2)
        else:
            area = dim
        super().__init__(pos, area, align, parent=parent, threed=False)
        self.mouse_loc = None
        self.loc = self.rect.centerx
        self.min = self.parent.rect.left + self.rect.w / 2 + self.parent.rect.h
        self.max = self.parent.rect.right - self.rect.w / 2 - self.parent.rect.h
        self.normal_colour = col
        self.surface.set_colorkey(white)
        self.update()

    def handle(self, event, mouse):
        state = self.state
        if self.on_top(mouse):
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed(3)[0] and \
                    self.state is not PRESS_STATE:
                self.state = PRESS_STATE
                self.mouse_loc = mouse[0]
                self.loc = self.rect.centerx
            elif event.type == pygame.MOUSEBUTTONUP and self.state is PRESS_STATE and \
                    not pygame.mouse.get_pressed(3)[0]:
                self.state = HIGHLIGHT_STATE
            if self.state is NORMAL_STATE:
                self.state = HIGHLIGHT_STATE
            if state != self.state:
                self.update()
            return True
        else:
            if self.state not in [PRESS_STATE, NORMAL_STATE]:
                self.state = NORMAL_STATE
            self.update()
            return False

    def set_loc(self, loc):
        self.loc = loc
        self.rect.centerx = loc

    def on_top(self, pos):
        if self.shape == 'circ':
            if ((pos[0] - self.rect.centerx) ** 2 + (pos[1] - self.rect.centery) ** 2) ** (1 / 2) < self.radius:
                return True
            else:
                return False
        else:
            return super().on_top(pos)

    def update(self):
        if self.shape == 'circ':
            self.update_colours()
            self.surface.fill(white)
            r = self.radius - 1
            pygame.gfxdraw.filled_circle(self.surface, r, r, r, self.colours[self.state])
            pygame.gfxdraw.aacircle(self.surface, r, r, r, self.colours[self.state])
            if self.tooltip_display is not None and not self.on_top(pygame.mouse.get_pos()):
                self.tooltip_display.hide()
                self.tooltip_display = None
            Widget.change = True
        else:
            super().update()

    def animate(self, move=None):
        mouse = pygame.mouse.get_pos()
        if self.mouse_loc is not None and self.state is PRESS_STATE:
            if not pygame.mouse.get_pressed(3)[0]:
                self.state = NORMAL_STATE
                self.update()
            if self.min - self.rect.w / 2 <= mouse[0] <= self.max + self.rect.w / 2:
                move = mouse[0] - self.mouse_loc
        if move is not None:
            if self.loc + move > self.max:
                self.loc = self.max
            elif self.loc + move < self.min:
                self.loc = self.min
            else:
                self.loc += move
            self.rect.centerx = self.loc
            self.mouse_loc = mouse[0]
            self.parent.effect.update_slider()
            Widget.change = True
        super().animate()

    def no_focus(self):
        if self.state is HIGHLIGHT_STATE:
            self.state = NORMAL_STATE
            self.update()


class Text(Widget):
    bref = {'f': "font", 'b': "bold", 'i': "italic", 'c': "colour", 'u': "underline", 'h': "hyperlink"}

    def __init__(self, text, position, font_size=BASE_FONT_SIZE, font=DEFAULT_FONT, align=CENTER,
                 width=None, height=None,
                 appearing=False, colour=black, background_colour=white, solid_background=False, default_alpha=255,
                 multiline=False, justify=LEFT, parent=None, margin=0, catchable=False, bold=False, italic=False,
                 underline=False, hyperlink=None, in_func=None, funcs=None):
        area = [1, 1]
        if width is not None:
            area[0] = width
        if height is not None:
            area[1] = height
        super().__init__(position, area, align=align, appearing=appearing,
                         default_alpha=default_alpha, parent=parent, catchable=catchable)
        self.text = text
        self.font_size = font_size
        self.font = font
        self.colour = colour
        self.multiline = multiline
        self.justify = justify
        self.width = width
        self.height = height
        self.background_colour = background_colour
        self.margin = margin
        self.solid_background = solid_background
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.hyperlink = hyperlink
        self.in_func = in_func
        self.features = {"font": self.font, "bold": self.bold, "italic": self.italic, "colour": self.colour,
                         "underline": self.underline, "hyperlink": self.hyperlink, "func": self.in_func}
        if funcs is None:
            funcs = []
        self.funcs = funcs

        self.char_height = text_size(self.font_size, self.font)[1]

        self.style = pygame.font.SysFont(self.font, self.font_size, bold=self.bold, italic=self.italic)
        self.style.set_underline(self.underline)

        self.update(text=self.text, align=align, pos=position)

    def make_surface(self):
        if not self.multiline or len(self.text) < 1:
            surface = self.make_line(self.text)[0]
        else:
            surface = self.multiline_surface(self.width, self.background_colour)
        self.surface = pygame.Surface((surface.get_width() + self.margin * 2,
                                       surface.get_height() + self.margin * 2))
        self.surface.fill(self.background_colour)
        if not self.solid_background:
            self.surface.set_colorkey(self.background_colour)
        self.surface.blit(surface, (self.margin, self.margin))

    def handle(self, event, mouse):
        if self.in_container(mouse):
            for c in self.components:
                if c.handle(event, mouse):
                    return True
        for e in self.components:
            e.handle(event, mouse)
        return False

    def update(self, text=None, align=None, pos=None):
        if text is not None:
            self.text = text
            self.make_surface()
        if pos is None and align is None:
            align = CENTER
            pos = self.rect.center
        elif align is None:
            align = self.alignment
        elif pos is None:
            pos = self.rect.center
        self.rect = self.surface.get_rect()
        self.contain_rect = self.rect.copy()
        self.align(align, pos)
        if type(self.parent).__name__ == "TextInput":
            self.parent.cursor_row = 0
            self.parent.cursor_col = self.parent.cursor_pos
        self.rect.width = self.surface.get_width()
        self.rect.height = self.surface.get_height()
        self.contain_rect = self.rect.copy()
        self.transparency()
        Widget.change = True

    @staticmethod
    def det_command_secs(text):
        command_secs = []
        # command_secs: [[beg, end], [beg, end], [beg, end], etc.]
        for i in range(len(text) - 1):
            if text[i] + text[i + 1] == "</":
                command_secs.append([i])
            elif text[i] + text[i + 1] == "/>":
                command_secs[-1].append(i + 1)
        return command_secs

    def assemble_commands(self, text):
        command_secs = self.det_command_secs(text)
        # Assembling displayed text and commands to effect to the text
        commands = []  # [{'c': (200, 100, 10), 'i': True}, etc.]
        texts = []  # [0: "Hello", 25: "Bob", etc.]
        point = 0
        order = []
        funcs: List[Any] = self.funcs.copy()
        for sec in command_secs:
            if point != sec[0]:
                texts.append(text[point:sec[0]])
                order.append(0)
            point = sec[0]
            sets = text[sec[0] + 2:sec[1] - 1].split('-')
            comm = {}
            for st in sets:
                if st == '':
                    continue
                elem = st.split()
                for i, el in enumerate(elem):
                    elem[i] = el.lower()
                if elem[0] in ["font", 'f']:
                    elem[0] = 'f'
                    if len(elem) < 2 or elem[1] in ["default", 'd'] or elem[1] not in pygame.font.get_fonts():
                        elem[1] = self.font
                elif elem[0] in ["colour", 'c']:
                    elem[0] = 'c'
                    if len(elem) < 2 or elem[1] in ["default", 'd']:
                        elem[1] = self.colour
                    else:
                        str_colour = ''.join(elem[1][1:-1].split()).split(',')
                        elem[1] = tuple([int(val) for val in str_colour])
                elif elem[0] in ["hyperlink", 'h']:
                    elem[0] = 'h'
                    if len(elem) < 2:
                        elem.append(2)
                elif elem[0] in ["italic", 'i', "bold", 'b', "underline", 'u']:
                    elem[0] = elem[0][0]
                    if len(elem) < 2:
                        elem.append(2)
                    else:
                        elem[1] = toolkit.translate_bool_string(elem[1], self.features[self.bref[elem[0]]])
                elif elem[0] in ["function", "func", "fc"]:
                    elem[0] = "fc"
                    elem.append(funcs.pop(0))
                comm[elem[0]] = elem[1]
                point = sec[1] + 1
            commands.append(comm)
            order.append(1)
        texts.append(text[point:])
        order.append(0)
        return order, texts, commands, command_secs

    def make_line(self, text, **kwargs):
        features = {
            "font": kwargs.get("font", self.font),
            "bold": kwargs.get("bold", self.bold),
            "italic": kwargs.get("italic", self.italic),
            "colour": kwargs.get("colour", self.colour),
            "underline": kwargs.get("unerline", self.underline),
            "hyperlink": kwargs.get("hyperlink", self.hyperlink),
            "func": kwargs.get("in_func", self.in_func)
        }
        if features["hyperlink"] is not None:
            h1 = 0
        else:
            h1 = None
        h2 = None
        if features["func"] is not None:
            f1 = 0
        else:
            f1 = None
        f2 = None
        line = kwargs.get("line", 0)

        order, texts, commands, command_secs = self.assemble_commands(text)

        # Building the surfaces based off the above information
        surfaces = []
        widths = []
        text_point = 0
        comm_point = 0
        for t in order:
            if t == 1:
                command = commands[comm_point]
                for prov in command:
                    change = command[prov]
                    if prov == 'h':
                        if h1 is None:
                            h1 = sum(widths)
                            if change == 2:
                                features["hyperlink"] = "https://" + texts[text_point]
                            else:
                                features["hyperlink"] = change
                        elif h2 is None:
                            h2 = sum(widths)
                            self.make_text_button(h1, h2, line, prov, features)
                            if change != 2:
                                h1 = h2
                                features["hyperlink"] = change
                            else:
                                h1 = None
                                features["hyperlink"] = None
                            h2 = None
                    elif prov == 'fc':
                        if f1 is None:
                            f1 = sum(widths)
                            features["func"] = change
                        elif f2 is None:
                            f2 = sum(widths)
                            self.make_text_button(f1, f2, line, prov, features)
                            features["func"] = None
                            h1 = None
                            h2 = None
                    elif change == 2:
                        features[self.bref[prov]] = (features[self.bref[prov]] is False)
                    else:
                        features[self.bref[prov]] = change
                comm_point += 1
            elif t == 0:
                style = pygame.font.SysFont(features["font"], self.font_size,
                                            bold=features["bold"], italic=features["italic"])
                style.set_underline(features["underline"])
                surf = style.render(texts[text_point], True, features["colour"], self.background_colour)
                widths.append(surf.get_width())
                surfaces.append(surf)
                text_point += 1
        if h1 is not None and h2 is None:
            h2 = sum(widths)
            self.make_text_button(h1, h2, line, 'h', features)
        if f1 is not None and f2 is None:
            f2 = sum(widths)
            self.make_text_button(f1, f2, line, 'fc', features)

        # Putting the surfaces together into one
        height = surfaces[0].get_height()
        surface = pygame.Surface((sum(widths), height))
        surface.fill(self.background_colour)
        surface.set_colorkey(self.background_colour)
        point = 0
        for i, surf in enumerate(surfaces):
            surface.blit(surf, (point, 0))
            point += widths[i]
        return surface, features

    def make_text_button(self, start, end, line, kind, features):
        b = Button((self.rect.x + start, self.rect.y + line * self.char_height),
                   (end - start, self.char_height), parent=self, border_thickness=0, threed=False,
                   visible=False)
        if kind == 'fc':
            b.callback(features["func"])
        elif kind == 'h':
            b.callback(functools.partial(webbrowser.open, features["hyperlink"]))
        self.components.append(b)

    def multiline_surface(self, width, background):
        og_text = self.text
        features = self.features.copy()
        order, texts, commands, command_secs = self.assemble_commands(og_text)
        lines = []
        pos = 0
        comm_point = 0
        line = ''
        newline = None
        line_width = 0
        while pos < len(og_text):
            if newline is not None:
                line = newline
                newline = None
                local_secs = self.det_command_secs(line)
                visible_txt = line
                for i in range(len(local_secs) - 1, -1, -1):
                    visible_txt = visible_txt[0:local_secs[i][0]] + visible_txt[local_secs[i][1] + 1:]
                line_width = text_size(self.font_size, features["font"], txt=visible_txt,
                                       bold=features["bold"], italic=features["italic"])[0]
            if comm_point < len(command_secs) and command_secs[comm_point][0] == pos:
                command = commands[comm_point]
                for prov in command:
                    change = command[prov]
                    if prov in 'fib':
                        if change == 2:
                            features[self.bref[prov]] = (features[self.bref[prov]] is False)
                        else:
                            features[self.bref[prov]] = change
                line += og_text[command_secs[comm_point][0]:command_secs[comm_point][1] + 1]
                pos = command_secs[comm_point][1] + 1
                if pos >= len(og_text):
                    break
                comm_point += 1
            char = og_text[pos]
            if char == '\n':
                lines.append(line)
                line = ''
                line_width = 0
            else:
                line += char
                line_width += text_size(self.font_size, features["font"], txt=char,
                                        bold=features["bold"], italic=features["italic"])[0]
                if line_width > width:
                    if char == ' ':
                        line = line[:-1]
                    else:
                        in_command = False
                        for i in range(len(line) - 1, -1, -1):
                            if not in_command:
                                if line[i] == ' ':
                                    newline = line[i + 1:]
                                    line = line[:i]
                                    break
                            if i > 0:
                                if line[i - 1] + line[i] == "/>":
                                    in_command = True
                                if line[i - 1] + line[i] == "</":
                                    in_command = False
                        else:
                            newline = line[-1]
                            line = line[:-1]
                    lines.append(line)
                    line = ''
                    line_width = 0
            pos += 1
        lines.append(line)
        height = len(lines) * self.char_height
        surface = pygame.Surface((width, height))
        surface.fill(background)
        surface.set_colorkey(background)
        features = self.features.copy()
        for i, line in enumerate(lines):
            subsurface, features = \
                self.make_line(line, font=features["font"], bold=features["bold"], italic=features["italic"],
                               colour=features["colour"], underline=features["underline"],
                               hyperlink=features["hyperlink"], in_func=features["func"], line=i)
            style = pygame.font.SysFont(features["font"], self.font_size, bold=features["bold"],
                                        italic=features["italic"])
            style.set_underline(features["underline"])
            if self.justify == CENTER:
                dest_x = (surface.get_width() - subsurface.get_width()) / 2
            elif self.justify == RIGHT:
                dest_x = surface.get_width() - subsurface.get_width()
            else:
                dest_x = 0
            surface.blit(subsurface, (dest_x, i * self.char_height))
        return surface


class BaseToolTip(Widget):
    instances = []
    alpha_rate = 10

    def __init__(self, pos, surface, align=LEFT, appearing=True, background_colour=black, tip=True, default_alpha=200):
        area = (surface.get_width(), surface.get_height())
        super().__init__(pos, area, align=align, default_alpha=default_alpha)
        if background_colour is not None:
            self.surface.fill(background_colour)
            self.surface.blit(surface, (0, 0))
        else:
            self.surface = surface
        self.appearing = appearing
        if self.appearing:
            self.surface.set_alpha(0)
        if tip:
            self.update(pygame.mouse.get_pos())

    def update(self, mouse):
        if self.rect.x != mouse[0] or self.rect.y != mouse[1] + TOOLTIP_OFFSET:
            self.rect.x = mouse[0]
            self.rect.y = mouse[1] + TOOLTIP_OFFSET
            if self.rect.right > screen_width:
                self.rect.right = self.rect.left
            if self.rect.bottom > screen_height:
                self.rect.bottom = self.rect.top - 2 * TOOLTIP_OFFSET
            Widget.change = True

    def catch(self, mouse):
        return False

    def show(self):
        BaseToolTip.instances.append(self)
        self.transparency()
        Widget.change = True

    def hide(self):
        BaseToolTip.instances.remove(self)
        Widget.change = True


class ToolTip(BaseToolTip):

    def __init__(self, text, pos, colour=whitish, background_colour=black, align=LEFT, appearing=True, tip=True):
        self.text = text
        if background_colour is None:
            canvas = black
        else:
            canvas = background_colour
        t = Text(self.text, pos, colour=colour, background_colour=canvas, margin=2)
        super().__init__(pos, t.surface, align=align, appearing=appearing, background_colour=background_colour, tip=tip)


class Image(Widget):

    def __init__(self, position, area, img_path, align=CENTER, catchable=False):
        self.img_path = img_path
        self.catchable = catchable

        surface = pygame.image.load(self.img_path)
        width, height = surface.get_size()
        self.cropped_x, self.cropped_y = area

        img_dimension_ratio = width / height
        area_dimension_ratio = self.cropped_x / self.cropped_y
        if img_dimension_ratio >= area_dimension_ratio:
            self.width = self.cropped_x
            self.height = int(self.width / width * height)
        else:
            self.height = self.cropped_y
            self.width = int(self.height / height * width)
        self.dimensions = (int(self.width), int(self.height))
        try:
            self.surface = pygame.transform.smoothscale(surface, self.dimensions)
        except ValueError:
            self.surface = pygame.transform.scale(surface, self.dimensions)
        super().__init__(position, area, align, self.surface, catchable=catchable)


class Display(Widget):

    def __init__(self, position, area, surface, align=CENTER, catchable=False):
        self.catchable = catchable
        width, height = surface.get_size()
        self.cropped_x, self.cropped_y = area

        img_dimension_ratio = width / height
        area_dimension_ratio = self.cropped_x / self.cropped_y
        if img_dimension_ratio >= area_dimension_ratio:
            self.width = self.cropped_x
            self.height = int(self.width / width * height)
        else:
            self.height = self.cropped_y
            self.width = int(self.height / height * width)
        self.dimensions = (int(self.width), int(self.height))
        try:
            self.surface = pygame.transform.smoothscale(surface, self.dimensions)
        except ValueError:
            self.surface = pygame.transform.scale(surface, self.dimensions)
        super().__init__(position, area, align, self.surface, catchable=catchable)


class ScrollDisplayBase(Widget):

    def __init__(self, pos, area, align=TOPLEFT, margin=0, total_size=None, parent=None, catchable=False):
        self.surface = pygame.Surface(area)
        super().__init__(pos, area, align, self.surface, parent=parent, catchable=catchable)
        self.margin = margin
        self.total_size = total_size
        self.contain_rect.top = self.rect.top + self.margin
        self.contain_rect.left = self.rect.left + self.margin
        self.contain_rect.h = self.rect.h - 2 * self.margin
        self.contain_rect.w = self.rect.w - 2 * self.margin

        self.scroll_velocity = 0
        self.scroll_pos = 0
        self.actual_pos = 0
        self.scroll_bar = None
        if self.total_size is not None and self.total_size > self.contain_rect.h:
            self.set_scroll_bar()

    def set_scroll_bar(self):
        scroll_bar = ScrollBar((self.contain_rect.right, self.contain_rect.top),
                               (DEFAULT_EDGE - 1, self.contain_rect.h), self)
        self.extensions.append(scroll_bar)
        self.scroll_bar = scroll_bar

    def handle(self, event, mouse):
        if self.on_top(mouse):
            if self.in_container(mouse):
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        self.scroll_up()
                        return True
                    elif event.button == 5:
                        self.scroll_down()
                        return True
                for c in self.components:
                    if c.handle(event, mouse):
                        return True
        for e in self.extensions:
            if e.handle(event, mouse):
                return True
        return False

    def animate(self):
        self.scroll_velocity = self.scroll_velocity * SCROLL_RESISTANCE
        self.scrolling(self.scroll_velocity)
        super().animate()

    def scrolling(self, change):
        self.scroll_pos += change
        v = round(self.scroll_pos - self.actual_pos)
        self.actual_pos += v
        if self.actual_pos < 0:
            self.overshot_up(v)
        elif self.contain_rect.h < self.total_size and self.actual_pos > self.total_size - self.contain_rect.h:
            self.overshot_down(v)
        else:
            self.scroll(v)

    def scroll_up(self):
        if self.actual_pos > 0:
            self.scroll_velocity -= SCROLL_SPEED

    def scroll_down(self):
        if self.actual_pos < self.total_size - self.contain_rect.h:
            self.scroll_velocity += SCROLL_SPEED

    def overshot_up(self, v=0):
        self.scroll(-self.actual_pos + v)
        self.scroll_pos = 0
        self.actual_pos = 0
        self.scroll_velocity = 0

    def overshot_down(self, v=0):
        self.scroll((self.total_size - self.contain_rect.h) - self.actual_pos + v)
        self.scroll_pos = self.total_size - self.contain_rect.h
        self.actual_pos = self.scroll_pos
        self.scroll_velocity = 0


class ScrollButtonDisplay(ScrollDisplayBase):

    def __init__(self, position, area, total_size: int, align=TOPLEFT, edge=DEFAULT_EDGE, button_size=None,
                 colour=light_grey, parent=None):
        super().__init__(position, area, align, margin=edge, total_size=total_size + SHADOW, parent=parent,
                         catchable=True)
        self.colour = colour
        self.surface.fill(self.colour)
        self.button_size = button_size

        self.select_buttons = []
        self.button_tags: Dict[str, Button] = {}

        self.draw_borders()


class ScrollDisplay(ScrollDisplayBase):

    def __init__(self, cont, pos, area, align=TOPLEFT, edge=0, total_size=None, parent=None):
        if total_size is None:
            total_size = cont[0].rect.unionall([c.rect for c in cont]).h
        super().__init__(pos, area, align, margin=edge, total_size=total_size, parent=parent, catchable=True)
        self.components.extend(cont)
        self.surface.fill(white)
        self.surface.set_colorkey(white)


class GraphDisplay(Widget):

    def __init__(self, position, area, dat, x_title=None, y_title=None, align=TOPLEFT,
                 x_min=None, x_max=None, y_min=None, y_max=None, leader=False, title=None, colours=None, istime=True,
                 max_y_max=None, step=1, initial_date=None, dat_points=None, vlines=None, vlines_width=150, intg=False):
        self.istime = istime
        if step != 1:
            self.dat = self.rescale(dat, step)
            self.dat_points = self.rescale(dat_points, step)
        else:
            self.dat = dat
            self.dat_points = dat_points
        if self.istime:
            self.initial_date: Date = initial_date
        if colours is None:
            colours = {}
        surface = pygame.Surface(area)
        super().__init__(position, area, align, surface)
        self.surface.fill(white)
        self.surface.set_colorkey(white)
        self.x_title = x_title
        self.y_title = y_title
        self.title = title
        self.leader = leader
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.max_y_max = max_y_max
        self.heading_font_size = int(BASE_FONT_SIZE * 3 / 2)
        self.heading_font_width, self.heading_font_height = text_size(self.heading_font_size)
        self.title_font_size = TITLE_SIZE
        self.title_font_width, self.title_font_height = text_size(self.title_font_size)
        self.colours = colours
        self.slopes = {}
        self.tips_mem: Dict[str, Text] = {}
        self.line_tips_mem: Dict[str, Text] = {}
        self.vlines = vlines
        self.vlines_width = vlines_width
        self.intg = intg
        self.place = None

        self.top_margin = self.rect.h / 12
        self.bottom_margin = self.rect.h / 12
        self.left_margin = self.rect.w / 12
        self.right_margin = self.rect.w / 12
        if self.title is not None:
            self.top_margin += self.title_font_height
        if x_title is not None:
            self.bottom_margin += self.heading_font_height
        if y_title is not None:
            self.left_margin += self.heading_font_height

        self.graph_rect = pygame.Rect((self.left_margin + self.rect.x, self.top_margin + self.rect.y),
                                      (self.rect.w - (self.left_margin + self.right_margin),
                                       self.rect.h - (self.top_margin + self.bottom_margin)))

        # Axis headings and Title
        self.set_titles()

        # Set up mins and maxes
        if self.x_min is None:
            self.x_min = min([min(self.dat[k].keys()) for k in self.dat])
        if self.x_max is None:
            self.x_max = self.get_x_max()  # current date
        x_range = self.x_max - self.x_min

        if self.y_min is None:
            self.y_min = min([min(self.dat[k].values()) for k in self.dat])
            self.y_min -= abs(self.y_min) / 4
        if self.y_max is None:
            self.y_max = max([max(self.dat[k].values()) for k in self.dat])
            self.y_max += abs(self.y_max) / 4
            if self.max_y_max is not None and self.y_max > self.max_y_max:
                self.y_max = self.max_y_max
        y_range = self.y_max - self.y_min

        # Determine magnitude of difference in the y-variable
        if y_range != 0:
            self.y_mag = int(math.log10(y_range))
            self.y_step = 10 ** self.y_mag
            while y_range / self.y_step < 6:
                if self.y_step >= 1:
                    lcf = toolkit.least_prime_factor(self.y_step)
                    self.y_step //= lcf
                    if lcf >= 5:
                        self.y_step *= 2
                else:
                    self.y_step /= 2
        else:
            self.y_mag = 0
            self.y_step = 1

        # Update extrema
        if y_min is None:
            self.y_min = (self.y_min / self.y_step - 1) * self.y_step
        if y_max is None:
            self.y_max = (self.y_max / self.y_step + 1) * self.y_step
        y_range = self.y_max - self.y_min

        # Determine scale factors for the sketching of the curves
        if x_range != 0:
            self.x_scale = self.graph_rect.w / x_range
        else:
            self.x_scale = self.graph_rect.w
        if y_range != 0:
            self.y_scale = self.graph_rect.h / y_range
        else:
            self.y_scale = self.graph_rect.h

        # Add vertical lines
        if self.vlines is not None:
            self.sketch_vlines()

        # Graph Axes
        self.sketch_axes()

        # Data points and curve creation
        if self.dat_points is not None:
            self.sketch_data()
        self.sketch_curves()

        # Determine slopes of segments
        links = copy.deepcopy(self.dat)
        for line in links:
            s = {}
            points = links[line]
            if len(points) >= 2:
                x1 = min(points.keys())
                y1 = points[x1]
                del points[x1]

                while len(points) >= 1:
                    x2 = min(points.keys())
                    y2 = points[x2]
                    del points[x2]

                    slope = (y2 - y1) / (x2 - x1)
                    s[x1] = slope

                    x1 = x2
                    y1 = y2
            self.slopes[line] = s

        self.at_line = None
        self.no_focus()

    @staticmethod
    def rescale(dat, step):
        ndat = {}
        for line, points in dat.items():
            ndat[line] = {}
            for x, y in points.items():
                ndat[line][x * step] = y
        return ndat

    def catch(self, mouse):
        if self.on_top(mouse):
            Widget.new_cursor_type = 0
            if self.graph_rect.y < mouse[1] < self.graph_rect.y + self.graph_rect.h and \
                    self.graph_rect.x - self.left_margin / 4 < mouse[0] < \
                    self.graph_rect.x + self.graph_rect.w:
                where = mouse[0] - self.graph_rect.x
                if where < 0:
                    where = 0
                self.moment(where / self.x_scale)
                defocus_button()
                return True
            else:
                self.no_focus()
        return False

    def no_focus(self):
        self.moment(self.get_x_max() - self.x_min)
        Widget.change = True

    def handle(self, event, mouse):
        if self.on_top(mouse):
            if self.graph_rect.y < mouse[1] < self.graph_rect.y + self.graph_rect.h:
                return True
        else:
            return False

    def get_x_max(self):
        return max([max(self.dat[k].keys()) for k in self.dat])

    def get_x_min(self):
        return min([min(self.dat[k].keys()) for k in self.dat])

    def moment(self, place):
        small = self.get_x_min() - self.x_min
        big = self.get_x_max() - self.x_min
        if place < small:
            place = small
        elif place > big:
            place = big
        if place >= 0:
            x = round(self.graph_rect.x + self.x_scale * place)
            y_vals = {}
            for line in self.dat.keys():
                val = self.get_val(line, place + self.x_min)
                if val is not None:
                    y_vals[line] = val
            if self.at_line is None:
                Widget.change = True
                surface = pygame.Surface((1, self.graph_rect.h))
                surface.fill(black)
                self.at_line = Widget((x, self.graph_rect.y), (1, self.graph_rect.h), surface=surface, default_alpha=50)
                self.set_tool_tips(place, x, y_vals)
                self.components.append(self.at_line)
                self.place = place
            else:
                if place != self.place:
                    Widget.change = True
                    self.at_line.rect.x = x
                    self.at_line.extensions.clear()
                    self.set_tool_tips(place, x, y_vals)
                    if self.at_line not in self.components:
                        self.components.append(self.at_line)
                    self.place = place

    def get_val(self, line, x):
        points = self.dat[line]
        if x in points.keys():
            ret = self.dat[line][x]
        else:
            bestx = None
            for relx in points.keys():
                if relx < x:
                    if bestx is None or bestx < relx:
                        bestx = relx
            try:
                ret = points[bestx] + (x - bestx) * self.slopes[line][bestx]
            except KeyError:
                ret = None
        return ret

    def set_tool_tips(self, place, x, y_vals):
        x_val = place + self.x_min
        order = sorted(list(y_vals.keys()), key=lambda line: y_vals[line])

        self.show_leader(order, x, x_val, y_vals)

        r = int(screen_height / 180) + 1
        offset = r * 2

        tips = []
        line_tips = []
        for line in order:
            y_val: float = y_vals[line]
            y_pos = self.rect.y + self.rect.h - ((y_val - self.y_min) * self.y_scale + self.bottom_margin)
            if line in self.colours:
                orig_colour = self.colours[line]
                colour = tuple(fade_colour(orig_colour))[:3]
            else:
                colour = grey
                orig_colour = colour
            if self.intg or self.y_mag > 2:
                txt = str(int(round(y_val)))
            else:
                txt = str(round(y_val, 2 - self.y_mag))
            if line in self.tips_mem.keys():
                num_tip = self.tips_mem[line]
                if txt == num_tip.text:
                    txt = None
                num_tip.update(txt, align=RIGHT, pos=(x - offset, y_pos))
            else:
                num_tip = Text(txt, (x - offset, y_pos), align=RIGHT,
                               colour=black, background_colour=colour, solid_background=True, margin=2)
                self.tips_mem[line] = num_tip
            num_tip.surface.set_alpha(200)
            tips.append(num_tip)

            if line in self.line_tips_mem.keys():
                line_tip = self.line_tips_mem[line]
                line_tip.update(align=LEFT, pos=(x + offset, y_pos))
            else:
                line_tip = Text(line, (x + offset, y_pos), align=LEFT,
                                colour=black, background_colour=colour, solid_background=True, margin=2)
                self.line_tips_mem[line] = line_tip
            line_tip.surface.set_alpha(200)
            line_tips.append(line_tip)

            s = Widget((x, round(y_pos)), (2 * r + 1, 2 * r + 1), align=CENTER)
            if orig_colour == black:
                back = grey
            else:
                back = light_grey
            s.surface.fill(back)
            s.surface.set_colorkey(back)
            pygame.gfxdraw.aacircle(s.surface, r, r, r, orig_colour)
            pygame.gfxdraw.filled_circle(s.surface, r, r, r, orig_colour)
            self.at_line.extensions.append(s)
        while True:
            for i in range(len(tips) - 1):
                dif = tips[i + 1].rect.bottom - tips[i].rect.top
                if dif > 0:
                    tips[i].rect.y += dif / 2
                    tips[i + 1].rect.y -= dif / 2
                    break
            else:
                break
        self.at_line.extensions.extend(tips)
        for i, tip in enumerate(line_tips):
            tip.rect.y = tips[i].rect.y
        self.at_line.extensions.extend(line_tips)

    def show_leader(self, order, x, x_val, y_vals):
        lead = None
        y_pos = self.rect.y + self.top_margin + self.graph_rect.h / 24
        if self.leader and len(order) >= 2:
            line = order[-1]
            if self.intg or self.y_mag > 2:
                dif = str(round(y_vals[line] - y_vals[order[-2]]))
            else:
                dif = str(round(y_vals[line] - y_vals[order[-2]], 2 - self.y_mag))
            if line in self.colours:
                colour = fade_colour(self.colours[line])
            else:
                colour = grey
            lead = Text(line + ' +' + dif, (x, y_pos), align=TOP, colour=black, background_colour=colour,
                        solid_background=True, margin=2)
            lead.surface.set_alpha(200)
            self.at_line.extensions.append(lead)
        if self.istime:
            txt = self.initial_date.get_date(int(x_val)).__repr__()
        else:
            txt = str(round(x_val))
        if lead is not None:
            pos = (lead.rect.centerx, lead.rect.top)
        else:
            pos = (x, y_pos)
        x_pos = Text(txt, pos, align=BOTTOM)
        self.at_line.extensions.append(x_pos)

    def set_titles(self):
        font_size = self.heading_font_size
        if self.x_title is not None:
            heading = Text(self.x_title,
                           (self.rect.x + self.rect.w / 2, self.rect.y + self.rect.h - self.bottom_margin / 4),
                           font_size=font_size)
            self.components.append(heading)
        if self.y_title is not None:
            heading = Text(self.y_title, (self.rect.x + self.left_margin / 2, self.rect.y + self.rect.h / 2),
                           font_size=font_size)
            heading.surface = pygame.transform.rotate(heading.surface, 90)
            x, y = heading.rect.center
            heading.rect = heading.surface.get_rect()
            heading.rect.center = (x, y)
            self.components.append(heading)
        if self.title is not None:
            title = Text(self.title, (self.graph_rect.x, self.rect.y + self.top_margin / 2),
                         font_size=self.title_font_size, align=LEFT)
            self.components.append(title)

    def sketch_vlines(self):
        for x, desc in self.vlines.items():
            posx = round(self.left_margin + (x - self.x_min) / (self.x_max - self.x_min) * self.graph_rect.w)
            pygame.gfxdraw.line(self.surface,
                                posx, round(self.top_margin + self.graph_rect.h),
                                posx, round(self.top_margin), dark_grey)
            t = Text(desc, (posx, self.top_margin), align=BOTTOM, width=self.vlines_width,
                     multiline=True, justify=RIGHT)
            t.surface = pygame.transform.rotate(t.surface, 90)
            t.rect = t.surface.get_rect()
            t.rect.topright = posx, self.top_margin
            self.components.append(t)

    def sketch_axes(self):
        zero_loc = None

        # Draw y-axis intervals
        font_size = BASE_FONT_SIZE
        num = int((self.y_max - self.y_min) / self.y_step)
        for i in range(num + 1):
            mark = round(self.y_min + self.y_step * i, 4)
            if mark == 0:
                zero_loc = self.graph_rect.bottom - self.graph_rect.h / num * i
            y = self.graph_rect.bottom - (self.y_step * i * self.y_scale)
            t = Text(str(mark), (self.graph_rect.left - BASE_FONT_SIZE / 2, y), font_size=font_size, align=RIGHT)
            self.components.append(t)
            y -= self.rect.top
            pygame.draw.line(self.surface, light_grey, (self.left_margin, y),
                             (self.left_margin + self.graph_rect.w, y))

        # Draw x-axis intervals
        step = 1
        num = self.x_max - self.x_min
        if self.y_max <= 0:
            alignment = BOTTOM
        else:
            alignment = TOP
        if self.istime:
            if num < 60:
                unit = 'day'
            elif num < 365 * 3:
                num = num / 30
                unit = 'month'
            else:
                num = num / 365
                unit = 'year'
            while num > 12:
                step *= 2
                num = num / 2
            place = self.x_min
            min_date = self.initial_date.get_date(place)
            if unit == 'month':
                if min_date != 1:
                    place += date_kit.get_month_length(min_date.month, min_date.year) + 1 - min_date.day
            elif unit == 'year':
                if min_date.month != 1 or min_date.day != 1:
                    place += date_kit.get_year_length(min_date.year) + 1 - min_date.day_of_year()
            # Button((self.graph_rect.left, self.rect.y), (self.graph_rect.right, self.rect.y + zero_loc)).show()
            while place <= self.x_max:
                date = self.initial_date.get_date(place)
                if unit == 'month':
                    txt = date_kit.months[date.month][:3] + ' ' + str(date.year)
                elif unit == 'year':
                    txt = str(date.year)
                else:
                    txt = date.__repr__()
                # print(self.graph_rect.left, place, self.x_min, self.x_scale)
                pos = (self.left_margin + (place - self.x_min) * self.x_scale, zero_loc)
                self.x_axis_label(txt, pos, alignment, font_size)
                self.x_axis_mark(pos)
                if unit == 'month':
                    y = date.year
                    m = date.month
                    for i in range(step):
                        if m > 12:
                            m -= 12
                            y += 1
                        place += date_kit.get_month_length(m, y)
                        m += 1
                elif unit == 'year':
                    place += sum([date_kit.get_year_length(date.year + i) for i in range(step)])
                elif unit == 'day':
                    place += step
        else:
            while num > 12:
                step *= 2
                num = num / 2
            for x in range(int(num) * step, -1, -step):
                txt = str(self.x_min + x)
                pos = (self.left_margin + x * self.x_scale, zero_loc)
                self.x_axis_label(txt, pos, alignment, font_size)
                self.x_axis_mark(pos)

        # Draw x-axis
        if self.y_min >= 0:
            zero_loc = self.top_margin + self.graph_rect.h  # Bottom
        elif self.y_max <= 0:
            zero_loc = self.top_margin  # Top
        pygame.draw.line(self.surface, black,
                         (self.left_margin, zero_loc), (self.left_margin + self.graph_rect.w, zero_loc))

    def x_axis_label(self, txt, pos, alignment, font_size):
        t = Text(txt, (pos[0] + self.rect.left, pos[1]), font_size=font_size, align=alignment)
        if alignment == BOTTOM:
            t.rect.bottom -= font_size * FONT_ASPECT
        else:
            t.rect.top += font_size * FONT_ASPECT
        # t.surface = pygame.transform.rotate(t.surface, 90)
        self.components.append(t)

    def x_axis_mark(self, pos):
        pygame.draw.line(self.surface, light_grey,
                         (pos[0], self.top_margin + self.graph_rect.h),
                         (pos[0], self.top_margin))

    def sketch_data(self):
        for line, points in self.dat_points.items():
            if line in self.colours:
                colour = list(self.colours[line])[:3] + [120]
            else:
                colour = list(grey) + [120]
            for x, ys in points.items():
                for y in ys:
                    p = (round(self.left_margin + ((x - self.x_min) * self.x_scale)),
                         round(self.rect.h - ((y - self.y_min) * self.y_scale + self.bottom_margin)))
                    if self.left_margin <= p[0] <= self.left_margin + self.graph_rect.w and \
                            self.top_margin <= p[1] <= self.top_margin + self.graph_rect.h:
                        pygame.gfxdraw.filled_circle(self.surface, p[0], p[1], 2, colour)
                        pygame.gfxdraw.aacircle(self.surface, p[0], p[1], 2, colour)

    def sketch_curves(self):
        order = sorted(self.dat.keys(), key=lambda line: self.dat[line][max(self.dat[line].keys())])
        for line in order:
            if line in self.colours:
                line_colour = self.colours[line]
            else:
                line_colour = grey
            points = []
            pp = None
            for x in sorted(self.dat[line].keys()):
                p = (round(self.graph_rect.w + self.left_margin - ((self.x_max - x) * self.x_scale)),
                     round(self.rect.h - ((self.dat[line][x] - self.y_min) * self.y_scale + self.bottom_margin)))
                if self.left_margin <= p[0] <= self.left_margin + self.graph_rect.w and \
                        self.top_margin <= p[1] <= self.top_margin + self.graph_rect.h:
                    if len(points) == 0 and pp is not None:
                        np = (round(self.graph_rect.x),
                              p[1] + round((pp[1] - p[1]) / (pp[0] - p[0]) * (self.graph_rect.x - p[0])))
                        points.append(np)
                    points.append(p)
                pp = p

            for j in range(len(points) - 1):
                pygame.draw.aaline(self.surface, line_colour, points[j], points[j + 1])
                radial_offset = 1.3
                num = 5
                for a in range(num):
                    angle = a * 2 * math.pi / num
                    x_offset = radial_offset * math.cos(angle)
                    y_offset = radial_offset * math.sin(angle)
                    pygame.draw.aaline(self.surface, line_colour,
                                       (points[j][0] + x_offset, points[j][1] + y_offset),
                                       (points[j + 1][0] + x_offset, points[j + 1][1] + y_offset))
                # if j < len(points) - 2:
                #     x1 = (points[j][0] + points[j + 1][0]) / 2
                #     x2 = (points[j + 1][0] + points[j + 2][0]) / 2
                #     y1 = (points[j][1] + points[j + 1][1]) / 2
                #     y2 = (points[j + 1][1] + points[j + 2][1]) / 2
                #     for a in range(num):
                #         angle = a * 2 * math.pi / num
                #         x_offset = radial_offset * math.cos(angle)
                #         y_offset = radial_offset * math.sin(angle)
                #         pygame.draw.aaline(self.surface, line_colour,
                #                            (x1 + x_offset, y1 + y_offset),
                #                            (x2 + x_offset, y2 + y_offset))

    def legend(self, order):
        notes = []
        full = Widget((self.graph_rect.right, self.rect.y), (self.right_margin, self.rect.h), align=TOPLEFT)
        full.surface.fill(white)
        full.surface.set_colorkey(white)
        for i, line in enumerate(order):
            if line in self.colours:
                colour = fade_colour(self.colours[line])
            else:
                colour = grey
            x = 10
            y = full.rect.h - self.bottom_margin
            note = Text(line, (x, y), colour=black, background_colour=colour, solid_background=True, align=LEFT,
                        default_alpha=200, margin=2)
            note.rect.y -= (self.dat[line][max(self.dat[line].keys())] - self.y_min) * self.y_scale
            notes.append(note)
        while True:
            for i in range(len(notes) - 1):
                dif = notes[i + 1].rect.bottom - notes[i].rect.top
                if dif > 0:
                    notes[i].rect.y += dif / 2
                    notes[i + 1].rect.y -= dif / 2
                    break
            else:
                break
        for note in notes:
            full.surface.blit(note.surface, note.rect)
        self.components.append(full)


class TextInput(Widget):

    def __init__(self, text, position, area, font_size=BASE_FONT_SIZE, font="couriernew", align=CENTER,
                 colour=whitish, background_colour=black, default_alpha=255,
                 multiline=False, justify=LEFT):
        super().__init__(position, area, align=align)
        self.surface.fill(background_colour)
        self.text = text
        self.multiline = multiline
        self.base_surface = self.surface.copy()
        self.cursor_pos = len(self.text)
        self.cursor_row = 0
        self.cursor_col = 0
        self.text_surface = Text(text, position, font_size=font_size, font=font, align=align,
                                 colour=colour, background_colour=background_colour, width=area[0], height=area[1],
                                 default_alpha=default_alpha, multiline=multiline, justify=justify, parent=self,
                                 margin=2)
        self.surface.blit(self.text_surface.surface, (0, 0))
        self.char_width, self.char_height = text_size(font_size, font, 'M')
        self.cursor = Widget((self.contain_rect.x + self.cursor_pos * self.char_width,
                              self.contain_rect.y + self.char_height * (self.cursor_row + 1) - self.char_height * 0.1),
                             (1, self.char_height * 0.8), align=BOTTOM)
        self.displacement = [0, 0]
        self.cursor.surface.fill(colour)
        self.components.append(self.cursor)

    def handle(self, event, mouse):
        if self.on_top(mouse):
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self in text_capture:
                    text_capture.remove(self)
                text_capture.append(self)
        if event.type == pygame.KEYDOWN and self in text_capture:
            do_update = True
            if event.key == pygame.K_LEFT:
                if self.cursor_pos > 0:
                    if event.mod == pygame.KMOD_LCTRL or event.mod == pygame.KMOD_RCTRL:
                        if self.text[self.cursor_pos - 1] in string.punctuation:
                            self.move_left()
                        else:
                            while self.cursor_pos > 0 and self.text[self.cursor_pos - 1] in string.whitespace:
                                self.move_left()
                            while self.cursor_pos > 0 and self.text[self.cursor_pos - 1].isalpha():
                                self.move_left()
                    else:
                        self.move_left()
            elif event.key == pygame.K_RIGHT:
                if self.cursor_pos < len(self.text):
                    if event.mod == pygame.KMOD_LCTRL or event.mod == pygame.KMOD_RCTRL:
                        if self.text[self.cursor_pos] in string.punctuation:
                            self.move_right()
                        else:
                            while self.cursor_pos < len(self.text) and self.text[self.cursor_pos] in string.whitespace:
                                self.move_right()
                            while self.cursor_pos < len(self.text) and self.text[self.cursor_pos].isalpha():
                                self.move_right()
                    else:
                        self.move_right()
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    if event.mod == pygame.KMOD_LCTRL or event.mod == pygame.KMOD_RCTRL:
                        if self.text[self.cursor_pos - 1] in string.punctuation:
                            self.backspace()
                        else:
                            while self.cursor_pos > 0 and self.text[self.cursor_pos - 1] in string.whitespace:
                                self.backspace()
                            while self.cursor_pos > 0 and self.text[self.cursor_pos - 1].isalpha():
                                self.backspace()
                    else:
                        self.backspace()
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    if event.mod == pygame.KMOD_LCTRL or event.mod == pygame.KMOD_RCTRL:
                        if self.text[self.cursor_pos] in string.punctuation:
                            self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                        else:
                            while self.cursor_pos < len(self.text) and self.text[self.cursor_pos] in string.whitespace:
                                self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                            while self.cursor_pos < len(self.text) and self.text[self.cursor_pos].isalpha():
                                self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
                    else:
                        self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
            elif event.key == pygame.K_RETURN and self.multiline:
                self.text = self.text[:self.cursor_pos] + '\n' + self.text[self.cursor_pos:]
                self.cursor_pos += 1
            elif event.key == pygame.K_SPACE:
                if self.cursor_pos != 0:
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += 1
            elif event.unicode in string.printable and event.unicode not in string.whitespace:
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1
            else:
                do_update = False
            if do_update:
                self.update()
                Widget.change = True
                return True
        return False

    def update(self):
        self.surface = self.base_surface.copy()
        self.text_surface.update(self.text)

        if self.multiline:
            if self.text_surface.rect.height > self.contain_rect.height:
                if self.text_surface.rect.height + self.displacement[1] < self.contain_rect.height:
                    self.displacement[1] = self.contain_rect.height - self.text_surface.rect.height
            else:
                self.displacement[1] = 0
        else:
            if self.text_surface.rect.width > self.contain_rect.width:
                if self.text_surface.rect.width + self.displacement[0] < self.contain_rect.width:
                    self.displacement[0] = self.contain_rect.width - self.text_surface.rect.width
            else:
                self.displacement[0] = 0

        self.cursor.rect.x = self.contain_rect.x + self.cursor_col * self.char_width + self.displacement[0]
        self.cursor.rect.bottom = self.contain_rect.y + self.char_height * (self.cursor_row + 1) + self.displacement[
            1] - self.char_height / 10
        if not self.multiline:
            if self.cursor.rect.right > self.contain_rect.x + self.contain_rect.w:
                self.displacement[0] -= (self.cursor.rect.right - (self.contain_rect.x + self.contain_rect.w))
                self.cursor.rect.x = self.contain_rect.x + self.cursor_col * self.char_width + self.displacement[0]
            if self.cursor.rect.left < self.contain_rect.x:
                self.displacement[0] += self.contain_rect.x - self.cursor.rect.left
                self.cursor.rect.x = self.contain_rect.x + self.cursor_col * self.char_width + self.displacement[0]
        else:
            if self.cursor.rect.bottom > self.contain_rect.y + self.contain_rect.h:
                self.displacement[1] -= (self.cursor.rect.bottom - (self.contain_rect.y + self.contain_rect.h))
                self.cursor.rect.bottom = self.contain_rect.y + self.char_height * (self.cursor_row + 1) + \
                    self.displacement[1]
            if self.cursor.rect.top < self.contain_rect.y:
                self.displacement[1] += self.contain_rect.y - self.cursor.rect.top
                self.cursor.rect.bottom = self.contain_rect.y + self.char_height * (self.cursor_row + 1) + \
                    self.displacement[1]

        self.surface.blit(self.text_surface.surface, self.displacement)

    def backspace(self):
        self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
        self.text_surface.text = self.text
        self.cursor_pos -= 1

    def move_right(self):
        self.cursor_pos += 1

    def move_left(self):
        self.cursor_pos -= 1


class PopUp(Widget):
    instances = []
    alpha_rate = 32

    def __init__(self, pos, area, surface=None, close=True, moveable=True, kind=None, unique=False, opacity=220,
                 align=CENTER, appearing=True, borders=True):
        self.kind = kind
        if unique and self.kind is not None and self.kind in [instance.kind for instance in PopUp.instances]:
            for instance in PopUp.instances:
                if instance.kind == self.kind:
                    instance.close()
        self.dragged = False
        self.moveable = moveable
        self.rel = None
        super().__init__(pos, area, surface=surface, align=align, default_alpha=opacity, appearing=appearing)
        if close:
            size = screen_height / 40 + 1
            self.close_b: Button \
                = Button((self.rect.right, self.rect.top), (size, size), align=TOPRIGHT,
                         colour=(200, 20, 20), border_thickness=2, parent=self, threed=False,
                         border_colour=gold)
            m = size * 3 / 4
            surf = pygame.Surface((m, m))
            surf.fill(white)
            surf.set_colorkey(white)
            pygame.draw.line(surf, gold, (0, 0), (m, m), width=3)
            pygame.draw.line(surf, gold, (0, m), (m, 0), width=3)
            cross = Widget(self.close_b.rect.center, (m, m), align=CENTER, surface=surf, catchable=False)
            self.close_b.components.append(cross)
            self.close_b.callback(self.close)
            self.components.append(self.close_b)
        else:
            self.close_b = None
        if borders:
            self.draw_borders(thickness=2, color=gold)
        PopUp.instances.append(self)

    def handle(self, event, mouse):
        if self.dragged:
            x = (mouse[0] - self.rel[0]) - self.rect.x
            y = (mouse[1] - self.rel[1]) - self.rect.y
            if self.rect.left + x < 0:
                x = -self.rect.left
            elif self.rect.right + x > screen_rect.right:
                x = screen_rect.right - self.rect.right
            if self.rect.top + y < 0:
                y = -self.rect.top
            elif self.rect.bottom + y > screen_rect.bottom:
                y = screen_rect.bottom - self.rect.bottom
            self.move(x, y)
        if self.on_top(mouse):
            for c in self.components:
                if c.handle(event, mouse):
                    break
            else:
                if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed(3)[0] and not self.dragged and \
                        self.moveable:
                    self.dragged = True
                    if PopUp.instances[-1] != self:
                        PopUp.instances.remove(self)
                        PopUp.instances.append(self)
                        Widget.change = True
                    self.rel = [mouse[0] - self.rect.x, mouse[1] - self.rect.y]
                elif event.type == pygame.MOUSEBUTTONUP and not pygame.mouse.get_pressed(3)[0] and self.dragged:
                    self.dragged = False
            return True
        else:
            for e in self.extensions:
                if e.handle(event, mouse):
                    return True
            return False

    def close(self):
        if not self.fading:
            PopUp.instances.remove(self)
            del self
        else:
            if self.close_b is not None:
                self.close_b.disable()
            self.disappearing = True

    def disappear(self, alpha_ratio, first=True):
        Widget.change = True
        alpha_rate = alpha_ratio * self.default_alpha
        if first and self.surface.get_alpha() - alpha_rate <= 0:
            PopUp.instances.remove(self)
            del self
            return
        else:
            self.surface.set_alpha(self.surface.get_alpha() - alpha_rate)
            for c in self.components + self.extensions:
                c.disappear(alpha_ratio, first=False)


class DragContainer(Widget):
    def __init__(self, parts=None, limited=False):
        super().__init__((0, 0), (0, 0))
        if parts is not None:
            self.extensions = parts
        self.dragged = False
        self.rel = None
        self.limited = limited

    def handle(self, event, mouse):
        if self.dragged:
            dx = mouse[0] - self.rel[0]
            dy = mouse[1] - self.rel[1]
            for e in self.extensions:
                e.move(dx, dy)
            self.rel[0] += dx
            self.rel[1] += dy
        if self.on_top(mouse):
            if event.type == pygame.MOUSEBUTTONDOWN and pygame.mouse.get_pressed(3)[0] and not self.dragged:
                self.dragged = True
                self.rel = [mouse[0] - self.rect.x, mouse[1] - self.rect.y]
            elif event.type == pygame.MOUSEBUTTONUP and not pygame.mouse.get_pressed(3)[0] and self.dragged:
                self.dragged = False
                self.rel = None

    def on_top(self, pos):
        if not self.limited:
            return True
        else:
            for e in self.extensions:
                if e.on_top(pos):
                    return True
            else:
                return False

    def add_part(self, part):
        self.extensions.append(part)

    def remove_part(self, part):
        self.extensions.remove(part)



def set_highlight_colour(shade):
    shade = shade * colour_ratio
    if shade > 255:
        return 255
    else:
        return shade


def set_press_colour(shade):
    shade = shade / colour_ratio
    if shade < 0:
        return 0
    else:
        return shade


def fade_colour(colour, amount=128):
    if colour not in faded_colours:
        faded_colours[colour] = {}
    if amount not in faded_colours[colour]:
        blanket = pygame.Surface((1, 1))
        blanket.fill(whitish)
        blanket.set_alpha(amount)
        paint = pygame.Surface((1, 1))
        paint.fill(colour)
        paint.blit(blanket, (0, 0))
        final = paint.get_at((0, 0))
        faded_colours[colour][amount] = final
    return faded_colours[colour][amount]


text_sizes = {}


def text_size(font_size, font=DEFAULT_FONT, txt='M', bold=False, italic=False):
    if (font, font_size, txt, bold, italic) in text_sizes:
        font_width, font_height = text_sizes[(font, font_size, txt, bold, italic)]
    else:
        font_width, font_height = pygame.font.SysFont(font, font_size, bold, italic).size(txt)
        text_sizes[(font, font_size, txt, bold, italic)] = (font_width, font_height)
    return font_width, font_height


def update():
    for widget in widgets:
        widget.update()


def set_cursor(num):
    if num == 0:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
    elif num == 1:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)


class LoadingScreen(Widget):
    alpha_rate = 20
    instances = []

    def __init__(self, surface, func, thread=None):
        self.func = func
        self.thread = thread
        if self.thread is not None:
            self.thread.start()
        super().__init__((0, 0), (screen_width, screen_height), surface=surface, appearing=True)

        # loading = Text("Loading...", screen_center, 20)
        # self.surface.blit(loading.surface, loading.rect)
        self.show()

    def animate(self):
        if self.surface.get_alpha() == 255:
            if self.thread is not None:
                self.thread.join()
            self.func()
            self.disappearing = True
        super().animate()

    def handle(self, event, mouse):
        return True

    def show(self):
        LoadingScreen.instances.append(self)

    def hide(self):
        LoadingScreen.instances.remove(self)


def terminate():
    pygame.quit()
    raise SystemExit


def update_display(wids, background):
    screen.blit(background, (0, 0))
    for widget in wids:
        widget.display()
    pygame.display.update()
    Widget.change = False


def run_loop(lock: threading.Lock,
             get_wids: Optional[Callable[[], List[Widget]]] = None,
             background: Optional[pygame.Surface] = None,
             fps: int = 60,
             show_fps: bool = True,
             escape: bool = True,
             channel: Any = None):

    def get_all_wids() -> List[Widget]:
        return get_wids() + [fps_txt]

    def default_wids() -> List[Widget]:
        return widgets + PopUp.instances + BaseToolTip.instances + LoadingScreen.instances

    if get_wids is None:
        get_wids = default_wids

    if background is None:
        background = pygame.Surface((screen_width, screen_height))
        background.fill(black)

    old_mouse = pygame.mouse.get_pos()
    frame = 0
    t = time.time()
    background_colour = background.get_at(screen_rect.center)
    if sum(background_colour[:3]) < 50:
        txt_colour = whitish
    else:
        txt_colour = black
    fps_txt = Text('', screen_rect.bottomright, align=BOTTOMRIGHT,
                   colour=txt_colour,
                   background_colour=background_colour)
    while True:
        mouse = pygame.mouse.get_pos()

        # handle events
        all_wids = get_all_wids()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or \
                    (escape and event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE):
                terminate()
            elif event.type == pygame.USEREVENT:
                if channel is not None:
                    channel.new_track()
            elif event.type == pygame.KEYDOWN and len(text_capture) > 0:
                for i in range(len(text_capture)):
                    if text_capture[-(i + 1)].handle(event, pygame.mouse.get_pos()):
                        break
            else:
                for i in range(len(all_wids)):
                    if len(all_wids) > i:
                        w = all_wids[-(i + 1)]
                        if w.handle(event, mouse):
                            break

        # animate
        all_wids = get_all_wids()
        for widget in all_wids:
            widget.animate()

        # catch mouse
        all_wids = get_all_wids()
        if mouse != old_mouse or Widget.change:
            for i in range(len(all_wids)):
                if len(all_wids) > i:
                    w = all_wids[-(i + 1)]
                    if w.catch(mouse):
                        break
            else:
                for w in set(widgets):
                    w.no_focus()
                if Button.focus is not None:
                    Button.focus.no_focus()
                Widget.new_cursor_type = 0

        # check cursor type
        if Widget.cursor_type != Widget.new_cursor_type:
            Widget.cursor_type = Widget.new_cursor_type
            if Widget.cursor_type == 0:
                set_cursor(0)
            elif Widget.cursor_type == 1:
                set_cursor(1)

        # display
        with lock:
            all_wids = get_all_wids()
            if Widget.change:
                update_display(all_wids, background)
            old_mouse = mouse

        if show_fps:
            frame += 1
            nt = time.time()
            dif = nt - t
            if dif >= 1:
                fps_txt.update(str(round(frame / dif)) + ' ' + 'FPS', align=BOTTOMRIGHT, pos=screen_rect.bottomright)
                t = nt
                frame = 0
        clock.tick(fps)
