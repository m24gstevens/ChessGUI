"""Sets up the graphical user interface"""

import copy
from tkinter import *
from PIL import ImageTk, Image

BOARD_SIZE = 512
BOARD_DIMENSIONS = 8
SQ_SIZE = BOARD_SIZE // BOARD_DIMENSIONS
PIECE_CODES = ['bK', 'bQ', 'bR', 'bB', 'bN', 'bP', 'wK', 'wQ', 'wR', 'wB', 'wN', 'wP']
STARTING_COORDS = {'wP': [(i,1) for i in range(8)], 'bP':[(i,6) for i in range(8)],
                   'wK': [(4, 0)], 'wQ': [(3,0)], 'wR': [(0,0), (7,0)], 'wB': [(2,0),(5,0)], 'wN': [(1,0),(6,0)],
                   'bK': [(4,7)], 'bQ': [(3,7)], 'bR': [(0,7), (7,7)], 'bB': [(2,7),(5,7)], 'bN': [(1,7),(6,7)],}

STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
STARTING_FLAGS = {'wk': True, 'wq': True, 'bk': True, 'bq': True, 'next_move':'w',
                  'ep_target':None, 'repetition_ct':0, 'halfmove_clock': 0, 'move_number': 1}

FILES = ['a','b','c', 'd','e','f','g','h']
RANKS = ['1','2','3','4','5','6','7','8']
IMAGE_CODES = ['dark', 'light', 'bK-dark', 'bQ-dark', 'bR-dark', 'bB-dark', 'bN-dark',
               'bP-dark', 'wK-dark', 'wQ-dark', 'wR-dark', 'wB-dark', 'wN-dark', 'wP-dark',
               'bK-light', 'bQ-light', 'bR-light', 'bB-light', 'bN-light',
               'bP-light', 'wK-light', 'wQ-light', 'wR-light', 'wB-light', 'wN-light', 'wP-light',]
FEN_CORRESPONDENCES = {'p':'bP','k':'bK','q':'bQ','r':'bR','n':'bN','b':'bB',
                       'P':'wP', 'K':'wK', 'Q':'wQ', 'R':'wR', 'N':'wN', 'B':'wB'}
REVERSED_CORRESPONDENCES = {'bP':'p','bK':'k','bQ':'q','bR':'r','bN':'n','bB':'b',
                       'wP':'P', 'wK':'K', 'wQ':'Q', 'wR':'R', 'wN':'N', 'wB':'B'}

#TODO: Two "Modes": Analysis mode and Game mode
# Analysis mode = can move in previous positions and alter course of ongoing game
# Game mode = can't move in previous positions, only see (i.e. what we have now)
#TODO: Create an AnalysisBoard class
#TODO: Find a way to select between the two classes on starting a new game (Tricky part!!!)

#TODO: Frame for storing moves made
#TODO: Make this frame interact with the game history


def delayed(function, argument):
    return lambda: function(argument)

def sequentially(*funcs):
    for funct in funcs:
        funct()

def fen_to_gameboard(fen_string):
    piece_configuration, space, extra_descriptors = fen_string.partition(' ')
    coordinates = {}
    row_idx = 7
    col_idx = 0
    for character in piece_configuration:
        if character == '/':
            row_idx -= 1
            col_idx = 0
            continue
        if character.isnumeric():
            for i in range(int(character)):
                coordinates[(col_idx, row_idx)] = ''
                col_idx += 1
        else:
            coordinates[(col_idx, row_idx)] = FEN_CORRESPONDENCES[character]
            col_idx += 1

    fields = extra_descriptors.split(' ')
    flags = {'next_move': fields[0], 'halfmove_clock': int(fields[3]), 'move_number': int(fields[4]),
             'repetition_ct': 0,
             'ep_target': None if fields[2] == '-' else square_to_coords(fields[2])}
    if fields[1] != '-':
        if 'k' in fields[1]:
            flags['bk'] = True
        if 'q' in fields[1]:
            flags['bq'] = True
        if 'K' in fields[1]:
            flags['wk'] = True
        if 'Q' in fields[1]:
            flags['wq'] = True

    resultingGameboard = GameBoard({}, flags)
    resultingGameboard.set_all_squares(coordinates)
    return resultingGameboard

def square_to_coords(square_string):
    """Takes a square as a string, like 'A1', and returns in-board coordinates"""
    x_coord = FILES.index(square_string[0])
    y_coord = RANKS.index(square_string[1])
    return (x_coord, y_coord)

def coords_to_square(coord):
    """Goes coordinates (W.r.t. 'A1' square) into a string representing the square"""
    x_coord, y_coord = coord
    return FILES[x_coord] + RANKS[y_coord]

def is_light(coord):
    x,y = coord
    return ((x+y) % 2 == 1)

def flip_coordinates(coord):
    """Flips in-board coordinates between white and black representations"""
    x,y = coord
    return (7-x, 7-y)

def convert_coords(board_coords):
    """Takes in-board coordinates WRT 'A1' square, and outputs coordinates to be used in
    images (With respect to origin at top left corner"""
    x_board, y_board = board_coords
    x_image = SQ_SIZE * x_board
    y_image = SQ_SIZE * (7 - y_board)
    return (x_image, y_image)


class GameBoard:
    def __init__(self, piece_positions, flags):
        piece_coordinates = {}
        for piece_code in piece_positions:
            for coordinate in piece_positions[piece_code]:
                piece_coordinates[coordinate] = piece_code
        self.all_squares = {(x,y): piece_coordinates.get((x,y), "")
                             for x in range(BOARD_DIMENSIONS) for y in range(BOARD_DIMENSIONS)}
        self.flags = copy.deepcopy(flags)
        """flags should be a dictionary, with (potential) keys of each side castling kingside or queenside,
         threefold repetition counter, whose move it is, halfmove clock (for 50 move rule) and turn counter"""

    def can_castle(self, option):
        """Takes colour (w or b) and side (k or q) and returns whether castling that way is permitted"""
        return self.flags.get(option, False)

    def whose_move(self):
        return self.flags["next_move"]

    def update_move_counters(self):
        if self.flags["next_move"] == 'b':
            self.flags["next_move"] = 'w'
            self.flags['move_number'] += 1
        else:
            self.flags["next_move"] = 'b'

    def update_halfmove_clock(self, from_coord, to_coord):
        if self.all_squares[to_coord] or self.all_squares[from_coord][1] == 'P':
            self.flags['halfmove_clock'] = 0
        else:
            self.flags['halfmove_clock'] = self.flags['halfmove_clock'] + 1

    def make_move(self, from_coord, to_coord):
        self.all_squares[to_coord] = self.all_squares[from_coord]
        self.all_squares[from_coord] = ''

    def set_all_squares(self, new_square_set):
        self.all_squares = new_square_set

    def make_fen(self):
        ep_square = coords_to_square(self.flags['ep_target']) if self.flags['ep_target'] else '-'
        if any({self.can_castle(option) for option in ['wk','wq','bk','bq']}):
            castling_string = ''.join([(op[1].upper() if op[0]=='w' else op[1]) if self.can_castle(op)
                                       else '' for op in ['wk','wq','bk','bq']])
        else:
            castling_string = '-'
        extra_descriptors = ' '.join([self.flags['next_move'], castling_string, ep_square,
                                      str(self.flags['halfmove_clock']), str(self.flags['move_number'])])

        piece_chars = []
        empty_counter = 0
        for row in range(7,-1,-1):
            for col in range(8):
                piece = self.all_squares[(col, row)]
                if piece:
                    if empty_counter == 0:
                        piece_chars.append(REVERSED_CORRESPONDENCES[piece])
                    else:
                        piece_chars.append(str(empty_counter))
                        piece_chars.append(REVERSED_CORRESPONDENCES[piece])
                        empty_counter = 0
                else:
                    empty_counter += 1
            if empty_counter != 0:
                piece_chars.append(str(empty_counter))
            empty_counter = 0
            piece_chars.append('/')
        piece_string = ''.join(piece_chars[:-1])

        return piece_string + ' ' + extra_descriptors


class CanvasFrame(Frame):
    def __init__(self, parent, width, height):
        super(CanvasFrame, self).__init__(parent, borderwidth=0, highlightthickness=0)

        self.canvas = Canvas(self, width=width, height=height, bd=4)
        self.canvas.pack()


    def add(self, widget, x, y):
        canvas_window = self.canvas.create_window(x,y, anchor=NW, window=widget)
        return widget


class DisplayBoard(CanvasFrame):
    """Deals with displaying pieces on the board and functions like flipping it."""
    def __init__(self, parent, board_state, images):
        super(DisplayBoard, self).__init__(parent, BOARD_SIZE, BOARD_SIZE)
        self.parent_frame = parent
        self.board_state = board_state  # Dictionary of coordinates -> pieces, changed when flipped
        self.square_buttons = {}
        self.IMAGES = images
        self.is_flipped = False
        for coord in self.board_state:
            theButton = Button(root, width = SQ_SIZE - 2, height = SQ_SIZE - 2, bd = 1)
            self.square_buttons[coord] = theButton
            x_board, y_board = convert_coords(coord)
            self.add(self.square_buttons[coord], x_board, y_board)

    def filename(self, coordinate):
        """Examines coordinates in the square_state dictionary and returns appropriate filename
        which will access the image relating to that square"""
        light_or_dark = ('light' if is_light(coordinate) else 'dark')
        square_contents = self.board_state[coordinate]
        if square_contents:
            return square_contents + '-' + light_or_dark
        else:
            return light_or_dark

    def config_image(self, coord):
        """Puts the required image into the button at the required coordinate"""
        image_code = self.filename(coord)
        self.square_buttons[coord].config(image=self.IMAGES[image_code])

    def load_all_images(self):
        """Loads all images"""
        for coord in self.board_state:
            self.config_image(coord)

    def flip_board(self):
        self.board_state = {flip_coordinates(coord): self.board_state[coord] for coord in self.board_state}
        self.load_all_images()
        self.is_flipped = not self.is_flipped
        flip_resign()

    def get_flipped_coordinates(self, coord):
        """Takes in 'True' coordinates within the board (Such as (0,0) for 'A1' square)
        , and returns coordinates to be used on the
        board state to account for flipping"""
        return flip_coordinates(coord) if self.is_flipped else coord

    def load_new_base(self, state_to_load):
        """Loads in a state to the .board_state attribute and reconfigures the images."""
        self.board_state = copy.deepcopy(state_to_load)
        self.load_all_images()


class InteractiveBoard(DisplayBoard):
    """Board that can be interacted with via piece movements"""
    def __init__(self, parent, game_state, images):
        super(InteractiveBoard, self).__init__(parent,
                                               copy.deepcopy(game_state.all_squares), images)
        self.game_state = game_state # A GameBoard object, unchanged when we flip

        for coord in self.square_buttons:
            self.square_buttons[coord].config(
                command = delayed(self.drag_drop, coord)) # The buttons link to their squares

        self.selected_square = None
        self.move_made = ''
        self.MoveWidget = Label(parent, relief=SUNKEN, width = 2, height=1,
                                bg="#FFFFFF" if self.game_state.whose_move() == 'w' else "#000000")
        self.Castles_Buttons = {
            'wk' : Button(parent, text="O-O", bg = "#ffffff"),
            'wq' : Button(parent, text="O-O-O", bg = "#ffffff"),
            'bk' : Button(parent, text="O-O", bg = "#000000", fg="#ffffff"),
            'bq' : Button(parent, text="O-O-O", bg = "#000000", fg="#ffffff")
        }
        self.can_claim_draw = False # Currently no threefold repetition detection.
        self.Claim_Draw = Button(parent, command = self.draw_game)

    def draw_game(self):
        draw_text = "D" + self.Claim_Draw.cget('text')[7:]
        GameOutcome.config(text = draw_text)
        self.activate_or_deactivate(DISABLED)


    def activate_or_deactivate(self, state_to_config):
        for coord in self.square_buttons:
            self.square_buttons[coord].config(state=state_to_config)
        for option in self.Castles_Buttons:
            self.Castles_Buttons[option].config(state=state_to_config)

    def drag_drop(self, coord):
        if self.selected_square is None:
            if self.board_state[coord]:
                if self.board_state[coord][0] == self.game_state.whose_move():
                    self.selected_square = coord
                    return
            self.selected_square = None
        else:
            if not self.invalid_move(coord):
                self.game_state.update_halfmove_clock(self.selected_square, coord)
                self.move(self.selected_square, coord)
                self.move_made = coords_to_square(self.get_flipped_coordinates(self.selected_square))\
                                 + coords_to_square(self.get_flipped_coordinates(coord))
                self.finish_turn()
            self.selected_square = None

    def invalid_move(self, coord):
        if self.selected_square == coord:
            return True
        else:
            if self.board_state[coord]:
                return self.board_state[coord][0] == self.board_state[self.selected_square][0]
        return False

    def move(self, from_coord, to_coord):
        pc = self.board_state[from_coord]
        self.board_state[to_coord] = pc
        self.config_image(to_coord)
        self.board_state[from_coord] = ''
        self.config_image(from_coord)
        self.game_state.make_move(from_coord, to_coord)

    def finish_turn(self):
        draw_last_turn = self.can_claim_draw
        self.game_state.update_move_counters()
        draw_next_turn = self.game_state.flags['repetition_ct'] > 2 or self.game_state.flags['halfmove_clock'] >= 100
        self.MoveWidget.config(bg = "#FFFFFF" if self.game_state.whose_move() == 'w' else "#000000")
        self.enable_castles_if_allowed()
        if not draw_last_turn:
            if draw_next_turn:
                self.Claim_Draw.grid(row=0, column=2)
                self.Claim_Draw.config(text = f"Claim draw by {'repetition' if self.game_state.flags['repetition_ct'] > 2 else '50 move rule'}")
        else:
            if not draw_next_turn:
                self.Claim_Draw.grid_forget()
        self.can_claim_draw = draw_next_turn

    def castle(self, option):
        """Option should be a colour followed by a side. Performs the castling operation on the board"""
        rank = 0 if option[0]=='w' else 7
        rook_position, king_target, rook_target = (0, 2, 3) if option[1] == 'q' else (7, 6, 5)
        king_from_coords = self.get_flipped_coordinates((4, rank))
        rook_from_coords = self.get_flipped_coordinates((rook_position, rank))
        king_to_coords = self.get_flipped_coordinates((king_target, rank))
        rook_to_coords = self.get_flipped_coordinates((rook_target, rank))
        self.move(king_from_coords, king_to_coords)
        self.move(rook_from_coords, rook_to_coords)
        for side in ['k','q']:
            self.game_state.flags.pop(option[0] + side, None)
        self.move_made = 'O-O' if option[1] == 'k' else 'O-O-O'
        self.finish_turn()
        self.game_state.flags['halfmove_clock'] += 1

    def enable_castles_if_allowed(self):
        for option in self.Castles_Buttons:
            if option[0] == self.game_state.whose_move() and self.game_state.can_castle(option):
                self.Castles_Buttons[option].config(state=NORMAL)
            else:
                self.Castles_Buttons[option].config(state=DISABLED)

    def initialize(self):
        self.load_all_images()
        for option in self.Castles_Buttons:
            self.Castles_Buttons[option].config(command = delayed(self.castle, option))
        self.enable_castles_if_allowed()

    def load_in(self, board_to_load):  # Make sure a new board is created when you pass it in to be loaded
        self.game_state = board_to_load
        self.load_new_base(copy.deepcopy(board_to_load.all_squares))
        self.selected_square = None
        self.is_flipped = False
        self.MoveWidget.config(bg="#FFFFFF" if self.game_state.whose_move() == 'w' else "#000000")
        self.enable_castles_if_allowed()


class HistoryBoard(InteractiveBoard):
    """Board that allows you to scroll through moves already made"""
    def __init__(self, parent, game_state, images):
        super(HistoryBoard, self).__init__(parent, game_state, images)
        self.analysis_mode = False
        self.starting_fen = self.game_state.make_fen()
        self.starting_repetition_ct = self.game_state.flags['repetition_ct']
        self.starting_halfmove_clk = self.game_state.flags['halfmove_clock']
        self.board_history = [(copy.deepcopy(self.game_state.all_squares), copy.deepcopy(self.game_state.flags))] # This will store the piece positions that will be loaded
        self.current_idx = 0 # Index of the current_game
        self.Movement_Buttons = { 'start': Button(parent, text='<<', state=DISABLED, command=self.start),
                                  'back': Button(parent, text='<', state=DISABLED, command = self.backwards),
                                  'next': Button(parent, text='>', state=DISABLED, command = self.forwards),
                                  'latest': Button(parent, text='>>', state=DISABLED, command = self.end) }
        self.Movement_Buttons['start'].grid(row=1, column=4)
        self.Movement_Buttons['back'].grid(row=1, column=5)
        self.Movement_Buttons['next'].grid(row=1, column=6)
        self.Movement_Buttons['latest'].grid(row=1, column=7)
        self.starting_colour = self.game_state.flags['next_move']
        self.moves_made = []
        self.scrolly = Scrollbar(root)
        self.scrolly.grid(row=1, column=3)
        self.displayer = Text(root, yscrollcommand = self.scrolly.set, width = 40)
        self.scrolly.config(command = self.displayer.yview)
        self.displayer.grid(row=1, column = 2)
        self.displayer.insert("end", "1." if self.starting_colour == 'w' else "1...")
        self.gamestring = []

    def process_move_text(self):
        recent_move = self.moves_made[-1]
        num_halfturns = len(self.moves_made)
        next_colour = self.game_state.flags['next_move'] # Make sure do this after updating the flags
        if next_colour == 'b':
            self.gamestring.append(recent_move)
            self.displayer.insert("end", ' ' + recent_move + ' ')
        else:
            turn_number = (num_halfturns + 3) // 2
            display_text = recent_move + ' ' + str(turn_number) + '. '
            self.gamestring.append(recent_move + ' ' + str(turn_number) + '.')
            self.displayer.insert("end", display_text)

    def reset_text(self):
        self.displayer.delete('1.0', 'end')
        self.displayer.insert("end", "1." if self.starting_colour == 'w' else "1...")

    def update_game_course(self):
        self.board_history = self.board_history[:self.current_idx]
        self.moves_made = self.moves_made[:self.current_idx - 1]
        self.gamestring = self.gamestring[:self.current_idx - 1]
        self.displayer.delete('1.0', 'end')
        self.displayer.insert("end", "1. " if self.starting_colour == 'w' else "1... ")
        self.displayer.insert("end", ' '.join(self.gamestring))

    def finish_turn(self):
        current_piece_position = copy.deepcopy(self.game_state.all_squares)
        self.game_state.flags['repetition_ct'] = self.board_history.count(current_piece_position)
        super().finish_turn()
        current_flags = copy.deepcopy(self.game_state.flags)
        self.current_idx += 1
        if self.current_idx != len(self.board_history):
            if current_piece_position != self.board_history[self.current_idx][0]:
                self.update_game_course()
        self.moves_made.append(self.move_made)
        self.process_move_text()
        self.board_history.append((current_piece_position, current_flags))
        if len(self.board_history) == 2:
            self.Movement_Buttons['start'].config(state=NORMAL)
            self.Movement_Buttons['back'].config(state=NORMAL)


    def load_in_position(self, index):
        if self.analysis_mode:
            if index == 0:
                starting_board = fen_to_gameboard(self.starting_fen)
                piece_state = starting_board.all_squares
                flag_state = starting_board.flags
                flag_state.update({'repetition_ct': self.starting_repetition_ct, 'halfmove_clock': self.starting_halfmove_clk})
            else:
                piece_state, flag_state = self.board_history[index]
            self.game_state = GameBoard({}, flag_state)
            self.game_state.set_all_squares(piece_state)
            self.board_state = piece_state
            self.selected_square = None
            if self.is_flipped:
                self.flip_board()
            self.load_all_images()
            self.enable_castles_if_allowed()
            if index % 2 == 0:
                self.MoveWidget.config(bg="#FFFFFF" if self.starting_colour == 'w' else "#000000")
            else:
                self.MoveWidget.config(bg="#000000" if self.starting_colour == 'w' else "#FFFFFF")

            self.current_idx = index
        else:
            self.board_state = self.board_history[index][0]
            if self.is_flipped:
                self.flip_board()
            self.load_all_images()
            if index != len(self.board_history) - 1:
                self.activate_or_deactivate('disabled')
            else:
                self.activate_or_deactivate(NORMAL)
                self.enable_castles_if_allowed()
            if index % 2 == 0:
                self.MoveWidget.config(bg="#FFFFFF" if self.starting_colour == 'w' else "#000000")
            else:
                self.MoveWidget.config(bg="#000000" if self.starting_colour == 'w' else "#FFFFFF")

            self.current_idx = index


    def update_movement_buttons(self, index):
        for option in self.Movement_Buttons:
            if option in ['start', 'back']:
                if index == 0:
                    self.Movement_Buttons[option].config(state=DISABLED)
                else:
                    self.Movement_Buttons[option].config(state=NORMAL)
            else:
                if index == len(self.board_history) - 1:
                    self.Movement_Buttons[option].config(state=DISABLED)
                else:
                    self.Movement_Buttons[option].config(state=NORMAL)

    def start(self):
        self.load_in_position(0)
        self.update_movement_buttons(0)

    def end(self):
        last_idx = len(self.board_history) - 1
        self.load_in_position(last_idx)
        self.update_movement_buttons(last_idx)

    def backwards(self):
        load_idx = self.current_idx - 1
        self.load_in_position(load_idx)
        self.update_movement_buttons(load_idx)

    def forwards(self):
        load_idx = self.current_idx + 1
        self.load_in_position(load_idx)
        self.update_movement_buttons(load_idx)

    def load_in(self, board_to_load):
        super().load_in(board_to_load)
        self.starting_colour = self.game_state.flags['next_move']
        self.board_history = [(copy.deepcopy(self.game_state.all_squares), copy.deepcopy(self.game_state.all_squares))]
        self.current_idx = 0
        self.moves_made = []


root = Tk()
root.title("M Chess")

PIECE_IMAGES = {pc : ImageTk.PhotoImage(Image.open(f"BoardImages/{pc}.png").resize((SQ_SIZE-2,SQ_SIZE-2)))
                for pc in IMAGE_CODES}

StartingGameboard = GameBoard(STARTING_COORDS, STARTING_FLAGS)

GameOutcome = Label(root)
GameOutcome.grid(row=0, column = 0)

def reset_game():
    GameOutcome.config(text='')
    mainBoard.activate_or_deactivate(NORMAL)
    mainBoard.reset_text()
    flip_resign()

BoardAndOptions = Frame(root)
BoardAndOptions.grid(row=1)

mainBoard = HistoryBoard(BoardAndOptions, StartingGameboard, PIECE_IMAGES)
mainBoard.grid(row=2, column = 0, rowspan = 8, columnspan = 8)

mainBoard.MoveWidget.grid(row=0, column = 8)

def resign_game():
    resign_text = f"{'White' if mainBoard.is_flipped else 'Black'} wins by resignation"
    mainBoard.activate_or_deactivate(DISABLED)
    GameOutcome.config(text = resign_text)

def draw_gme(reason):
    draw_text = "D" + reason[7:]
    mainBoard.activate_or_deactivate(DISABLED)
    GameOutcome.config(text = draw_text)

ResignButton = Button(BoardAndOptions, text='Resign', command=resign_game, bg='#FFFFFF')
ResignButton.grid(row=0, column=0)


def flip_resign():
    if mainBoard.is_flipped:
        ResignButton.config(bg='#000000', fg='#FFFFFF')
    else:
        ResignButton.config(bg='#FFFFFF', fg='#000000')

mainMenu = Menu(root)

def new_game():
    fenBoard = fen_to_gameboard(STARTING_FEN)
    mainBoard.load_in(fenBoard)
    reset_game()

def save_position():
    newWindow = Tk()
    newWindow.geometry("600x100")
    newWindow.title('Save Position')
    fenLabel = Label(newWindow, text='FEN')
    fenLabel.pack()
    fen_text = mainBoard.game_state.make_fen()
    fenReturn = StringVar(newWindow, value = fen_text)
    fenContainer = Entry(newWindow, textvariable = fenReturn, width=75)
    fenContainer.pack()
    exitButton = Button(newWindow, text="Done", command=newWindow.destroy)
    exitButton.pack()

    newWindow.mainloop()

def load_position():
    newWindow = Tk()
    newWindow.geometry("600x100")
    newWindow.title('Load Position')
    fenLabel = Label(newWindow, text='FEN')
    fenLabel.pack()
    fenContainer = Entry(newWindow, width=75)
    fenContainer.pack()

    def get_and_go():
        fen_text = fenContainer.get()
        fenBoard = fen_to_gameboard(fen_text)
        reset_game()
        mainBoard.load_in(fenBoard)
        newWindow.destroy()

    exitButton = Button(newWindow, text="Load", command=get_and_go)
    exitButton.pack()

    newWindow.mainloop()


fileMenu = Menu(mainMenu, tearoff=0)

fileMenu.add_command(label="New Game", command = new_game)
fileMenu.add_separator()
fileMenu.add_command(label="Load Position...", command=load_position)
fileMenu.add_command(label = "Load Game...")
fileMenu.add_separator()
fileMenu.add_command(label = "Save Position...", command=save_position)
fileMenu.add_command(label = "Save Game...")

mainMenu.add_cascade(label="File", menu = fileMenu)

def game_mode():
    mainBoard.analysis_mode = False

def analysis_mode():
    mainBoard.analysis_mode = True

modeMenu = Menu(mainMenu, tearoff=0)
modeMenu.add_command(label="Analysis mode", command = analysis_mode)
modeMenu.add_command(label="Game mode", command = game_mode)
mainMenu.add_cascade(label = "Mode", menu=modeMenu)

mainMenu.add_command(label="Flip", command=mainBoard.flip_board)

mainMenu.add_command(label="Exit", command=root.destroy)

root.config(menu=mainMenu)


mainBoard.Castles_Buttons['wk'].grid(row = 10, column = 0)
mainBoard.Castles_Buttons['wq'].grid(row = 10, column = 2)
mainBoard.Castles_Buttons['bk'].grid(row = 10, column = 4)
mainBoard.Castles_Buttons['bq'].grid(row = 10, column = 6)

mainBoard.initialize()

root.mainloop()

