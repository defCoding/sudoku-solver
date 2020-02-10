import csv
import itertools
import cProfile


''' Here is the plan for optimizing the code. At the moment, after each decision, we have to reevaluate the "value" of each cell (max number of constraints, or conversely, minimum number of available options). This leads to incredibly large amount of redundant calculations, however. If I try a value at cell c, then I only need to update the values of the cells in the box containing c, and in the row/column of c. To do this, I think it is best that I map cells to a list of valid options to keep track of how constrained the cells are. And from there, I will no longer to have to recalculate the options for each cell after every action. Instead, I only have to update cells that will be affected by filling in a given cell.

Upon trying out storing the valid options for a cell in a mapping data structures, I noticed about an 80% decrease in running time. However, it still is not significant enough to actually solve harder problems. With that in mind, I want to try implementing a more "human" logic to this. Whenever I do a sudoku board, and I don't find a cell with a single valid option, I check the other cells in the row/col/box and see if there is a shared value they cannot store. If they cannot store that shared value, then that cell must store the value. For example, in a 9x9 board, every row/col/box must store a 5. If cell X has multiple options including 5, and all the other cells in the same row/box/col do not have 5 as a valid option, then cell X must contain 5 and I can ignore all the other options.

Whenever a random value is attempted, then try out the logical deduction on the current state of the board over and over again until no more deductions can be made and return a list of all cells that were modified. If the current path fails, then undo all modifications.
 '''

class Board:
    def __init__(self, filename):
        self.n = 0
        self.n2 = 0

        # A mapping from a cell to the number in that cell.
        self.board = None

        # A mapping from a row/col/box # to a set of values contained in that box.
        self.vals_in_rows = None
        self.vals_in_cols = None
        self.vals_in_boxes = None

        # A mapping from a row/col/box # to a list of cells in that section.
        self.cells_in_rows = None
        self.cells_in_cols = None
        self.cells_in_boxes = None

        # A set of unsolved board spaces.
        self.unsolved_cells = None

        # The set of static cells (cells that were filled at the beginning of the game).
        self.static_cells = None

        # A mapping from a cell to the valid options for that cell. Those valid options are stored in a list of size n2.
        self.legal_options = None
        self.load_sudoku(filename)

    # Loads the sudoku board from the given file.
    def load_sudoku(self, filename):
        with open(filename) as csv_file:
            self.n = - 1
            reader = csv.reader(csv_file)

            for row in reader:
                if self.n == -1:
                    self.n = int(len(row) ** (1/2))
                    self.n2 = int(len(row))
                    self.board = {}

                    self.vals_in_rows = [set() for i in range(self.n2)]
                    self.vals_in_cols = [set() for i in range(self.n2)]
                    self.vals_in_boxes = [set() for i in range(self.n2)]
                    self.cells_in_rows = [set() for i in range(self.n2)]
                    self.cells_in_cols = [set() for i in range(self.n2)]
                    self.cells_in_boxes = [set() for i in range(self.n2)]

                    self.unsolved_cells = set(itertools.product(range(self.n2), range(self.n2)))
                    self.legal_options = {}
                    self.options_count = {}
                    self.static_cells = set()

                    # Add all cells to the correct row/col/box section.
                    for row_num in range(self.n2):
                        for col_num in range(self.n2):
                            self.cells_in_rows[row_num].add((row_num, col_num))

                    for col_num in range(self.n2):
                        for row_num in range(self.n2):
                            self.cells_in_cols[col_num].add((row_num, col_num))

                    for box_num in range(self.n2):
                        first_row = (box_num // self.n) * self.n
                        first_col = (box_num % self.n) * self.n

                        for i in range(self.n2):
                            self.cells_in_boxes[box_num].add((first_row + i // self.n, first_col + i % self.n))

                for col_num, item in enumerate(row):
                    val = 0 if item == '' else int(item)
                    row_num = reader.line_num - 1

                    self.board[(row_num, col_num)] = val
                    self.legal_options[(row_num, col_num)] = [False for i in range(self.n2)]
                    self.options_count[(row_num, col_num)] = 0


                    # If there is a value, mark it in its respective row/col/box
                    if val != 0:
                        self.vals_in_rows[row_num].add(val)
                        self.vals_in_cols[col_num].add(val)
                        self.vals_in_boxes[self.get_box_num((row_num, col_num))].add(val)
                        self.unsolved_cells.remove((row_num, col_num))
                        self.static_cells.add((row_num, col_num))


            # Fill in legal_options for every unsolved cell.
            for cell in self.unsolved_cells:
                for index in range(self.n2):
                    if self.is_legal_move(cell, index + 1):
                        self.legal_options[cell][index] = True
                        self.options_count[cell] += 1

    # prints out a command line representation of the board
    def print(self):
        for r in range(self.n2):
            # add row divider
            if r % self.n == 0 and not r == 0:
                if self.n2 > 9:
                    print("  " + "----" * self.n2)
                else:
                    print("  " + "---" * self.n2)

            row = ""

            for c in range(self.n2):

                val = self.board[(r,c)]

                # add column divider
                if c % self.n == 0 and not c == 0:
                    row += " | "
                else:
                    row += "  "

                # add value placeholder
                if self.n2 > 9:
                    if val ==  0: row += "__"
                    else: row += "%2i" % val
                else:
                    if val == 0: row += "_"
                    else: row += str(val)
            print(row)

    # Returns the box number containing a given cell.
    def get_box_num(self, cell):
        return self.n * (cell[0] // self.n) + cell[1] // self.n


    # Checks if a given value can legally be put in a given cell.
    def is_legal_move(self, cell, value):
        in_bounds = cell[0] >= 0 and cell[0] < self.n2 and cell[1] >= 0 and cell[1] < self.n2
        not_in_row = value not in self.vals_in_rows[cell[0]]
        not_in_col = value not in self.vals_in_cols[cell[1]]
        not_in_box = value not in self.vals_in_boxes[self.get_box_num(cell)]

        return in_bounds and not_in_row and not_in_col and not_in_box


    # Places a given value in a given cell.
    def make_move(self, cell, value):
        if cell in self.unsolved_cells:
            self.board[cell] = value
            self.vals_in_rows[cell[0]].add(value)
            self.vals_in_cols[cell[1]].add(value)
            self.vals_in_boxes[self.get_box_num(cell)].add(value)
            self.unsolved_cells.remove(cell)
            self.update_options_fill(cell, value)


    # Cleans out a given cell and makes it empty.
    def undo_move(self, cell):
        if cell not in self.unsolved_cells:
            prev_val = self.board[cell]
            self.board[cell] = 0
            self.vals_in_rows[cell[0]].discard(prev_val)
            self.vals_in_cols[cell[1]].discard(prev_val)
            self.vals_in_boxes[self.get_box_num(cell)].discard(prev_val)
            self.unsolved_cells.add(cell)
            self.update_options_clear(cell, prev_val)
            return prev_val

    # Cleans out every cell in a set of cells.
    def undo_all_moves(self, cells):
        undone_options = set()

        for cell in cells:
            undone_options.add(self.undo_move(cell))

        # Since the cells are removed sequentially, then their legal_options have to be recalculated. If cell A is removed before cell B, cell A's legal_options doesn't account for the fact that cell B will be removed.
        for cell in cells:
            self.recalculate_options(cell, undone_options)

    # Recalculates the options from a given list of options for a given cell.
    def recalculate_options(self, cell, options):
        for option in options:
            if self.is_legal_move(cell, option) and not self.legal_options[cell][option - 1]:
                self.legal_options[cell][option - 1] = True
                self.options_count[cell] += 1

    # Recalculates all legal options for a given list of cells.
    def recalculate_all_options(self, cells):
        for cell in cells:
            self.options_count[cell] = 0

            for option in range(1, self.n2 + 1):
                if self.is_legal_move(cell, option):
                    self.legal_options[cell][option - 1] = True
                    self.options_count[cell] += 1

    # Gets all the cells in a given box number.
    def get_box(self, box_num):
        return self.cells_in_boxes[box_num]

    # Gets all the cells in a given row.
    def get_row(self, row_num):
        return self.cells_in_rows[row_num]

    # Gets all the cells in a given column.
    def get_col(self, col_num):
        return self.cells_in_cols[col_num]

    # Get the cell with the most constraints (conversely, least legal options).
    def get_most_constrained_cell(self):
        min_options = self.n2 + 1
        min_cell = None

        for cell in self.unsolved_cells:
            num_options = self.options_count[cell]

            if num_options < min_options:
                min_options = num_options
                min_cell = cell

        return min_cell

    # Updates the legal options for a cell after another cell was filled.
    def update_options_fill(self, cell, value):
        for r_cell in self.get_row(cell[0]):
            if r_cell in self.unsolved_cells and r_cell not in self.static_cells and self.legal_options[r_cell][value - 1]:
                self.legal_options[r_cell][value - 1] = False
                self.options_count[r_cell] -= 1

        for c_cell in self.get_col(cell[1]):
            if c_cell in self.unsolved_cells and c_cell not in self.static_cells and self.legal_options[c_cell][value - 1]:
                self.legal_options[c_cell][value - 1] = False
                self.options_count[c_cell] -= 1

        for b_cell in self.get_box(self.get_box_num(cell)):
            if b_cell in self.unsolved_cells and b_cell not in self.static_cells and self.legal_options[b_cell][value - 1]:
                self.legal_options[b_cell][value - 1] = False
                self.options_count[b_cell] -= 1

    # Updates the legal options for a cell after another cell was cleared.
    def update_options_clear(self, cell, value):
        for r_cell in self.get_row(cell[0]):
            if r_cell in self.unsolved_cells and r_cell not in self.static_cells and self.is_legal_move(r_cell, value) and not self.legal_options[r_cell][value - 1]:
                self.legal_options[r_cell][value - 1] = True
                self.options_count[r_cell] += 1

        for c_cell in self.get_col(cell[1]):
            if c_cell in self.unsolved_cells and c_cell not in self.static_cells and self.is_legal_move(c_cell, value) and not self.legal_options[c_cell][value - 1]:
                self.legal_options[c_cell][value - 1] = True
                self.options_count[c_cell] += 1

        for b_cell in self.get_box(self.get_box_num(cell)):
            if b_cell in self.unsolved_cells and b_cell not in self.static_cells and self.is_legal_move(b_cell, value) and not self.legal_options[b_cell][value - 1]:
                self.legal_options[b_cell][value - 1] = True
                self.options_count[b_cell] += 1

    # Gets the count of legal options for a given cell.
    def get_num_options(self, cell):
        count = 0

        for opt in self.legal_options[cell]:
            if opt:
                count += 1

        return count

    # Determines if a given list of cells are in the same row.
    def in_same_row(self, cells):
        row = cells[0][0]

        for cell in cells:
            if cell[0] != row:
                return False

        return True

    # Determines if a given list of cells are in the same col.
    def in_same_col(self, cells):
        col = cells[0][1]

        for cell in cells:
            if cell[1] != col:
                return False

        return True

    # Determines if a given list of cells are in the same box.
    def in_same_box(self, cells):
        box = self.get_box_num(cells[0])

        for cell in cells:
            if self.get_box_num(cell) != box:
                return False

        return True

    # Removes an option for all cells in given row except for cells in given box. Returns all cells that were changed.
    def remove_options_row(self, option_to_remove, row, except_box_num):
        except_box = self.get_box(except_box_num)
        modified_cells = set()

        for r_cell in self.get_row(row):
            if r_cell not in except_box and r_cell in self.unsolved_cells and r_cell not in self.static_cells and self.legal_options[r_cell][option_to_remove]:
                self.legal_options[r_cell][option_to_remove] = False
                self.options_count[r_cell] -= 1
                modified_cells.add(r_cell)

        return modified_cells

    # Removes an option for all cells in given col except for cells in given box. Returns all cells that were changed.
    def remove_options_col(self, option_to_remove, col, except_box_num):
        except_box = self.get_box(except_box_num)
        modified_cells = set()

        for c_cell in self.get_col(col):
            if c_cell not in except_box and c_cell in self.unsolved_cells and c_cell not in self.static_cells and self.legal_options[c_cell][option_to_remove]:
                self.legal_options[c_cell][option_to_remove] = False
                self.options_count[c_cell] -= 1
                modified_cells.add(c_cell)

        return modified_cells

    # Removes an option for all cells in a given box except for cells in a given row/col. Returns all cells that were changed. row_or_col is 1 if except row, 0 if except col.
    def remove_options_box(self, option_to_remove, box_num, except_row_col, row_or_col):
        modified_cells = set()

        box = self.get_box(box_num)
        for b_cell in box:
            row_col = self.get_col(except_row_col) if row_or_col == 0 else self.get_row(except_row_col)

            if b_cell not in row_col and b_cell in self.unsolved_cells and b_cell not in self.static_cells and self.legal_options[b_cell][option_to_remove]:
                self.legal_options[b_cell][option_to_remove] = False
                self.options_count[b_cell] -= 1
                modified_cells.add(b_cell)

        return modified_cells

    # Gets the list of options for a given cell.
    def get_options(self, cell):
        return self.legal_options[cell]

class Solver:
    def __init__(self):
        pass

    def solveBoard(self, board):
        # Step deduce is a list of all modified cells after doing logical deduction once.
        deduced_singles = self.find_singles(board)
        deduced_boxes = self.deduce_boxes(board)
        deduced_cols = self.deduce_cols(board)
        deduced_rows = self.deduce_rows(board)

        deduced_cells = deduced_singles[0].union(deduced_boxes[0]).union(deduced_rows[0]).union(deduced_cols[0])

        modified_cells = deduced_boxes[1].union(deduced_rows[1]).union(deduced_cols[1])

        last_length = 0
        new_length = len(deduced_cells)

        # repeatedly do logical deduction until no more can be done.
        while new_length - last_length > 0:
            last_length = new_length

            deduced_singles = self.find_singles(board)
            deduced_boxes = self.deduce_boxes(board)
            deduced_cols = self.deduce_cols(board)
            deduced_rows = self.deduce_rows(board)

            deduced_cells = deduced_cells.union(deduced_singles[0]).union(deduced_boxes[0]).union(deduced_rows[0]).union(deduced_cols[0])
            modified_cells = modified_cells.union(deduced_boxes[1].union(deduced_rows[1]).union(deduced_cols[1]))

            new_length = len(deduced_cells)


        curr_cell = board.get_most_constrained_cell()

        if curr_cell is not None:
            options = board.get_options(curr_cell)

            for index, is_legal in enumerate(options):
                if is_legal:
                    board.make_move(curr_cell, index + 1)

                    if self.solveBoard(board):
                        return True
                    else:
                        board.undo_move(curr_cell)

            board.undo_all_moves(deduced_cells)
            board.recalculate_all_options(modified_cells)
            return False
        else:
            ret = len(board.unsolved_cells) == 0

            if not ret:
                board.undo_all_moves(deduced_cells)
                board.recalculate_all_options(modified_cells)

            return ret

    def deduce_rows(self, board):
        # A collection of all modified cells.
        filled_cells = set()
        modified_cells = set()

        for row in range(board.n2):
            # Counts how many cells have option (i + 1) [i is index] as a legal option.
            options_count = [0 for i in range(board.n2)]

            # Maps an option to the a list of cells that had it as a legal option.
            cells_for_option = {}
            for option in range(1, board.n2 + 1):
                cells_for_option[option] = []

            # Count options for all cells in row.
            for col in range(board.n2):
                cell = (row, col)

                if cell in board.unsolved_cells:
                    for index, is_legal in enumerate(board.get_options(cell)):
                        if is_legal:
                            options_count[index] += 1
                            cells_for_option[index + 1].append(cell)

            # If you find an option that only had one cell as its possible location, make a move there.
            for index, count in enumerate(options_count):
                if count == 1:
                    certain_cell = cells_for_option[index + 1][0]
                    filled_cells.add(certain_cell)
                    board.make_move(certain_cell, index + 1)
                elif count > 1 and count <= board.n:
                    corresponding_cells = cells_for_option[index + 1]
                    if board.in_same_box(corresponding_cells):
                        modified_cells.union(board.remove_options_box(index, board.get_box_num(corresponding_cells[0]), row, 1))

        return (filled_cells, modified_cells)

    def deduce_cols(self, board):
        # A collection of all modified cells.
        filled_cells = set()
        modified_cells = set()

        for col in range(board.n2):
            # Counts how many cells have option (i + 1) [i is index] as a legal option.
            options_count = [0 for i in range(board.n2)]

            # Maps an option to the a list of cells that had it as a legal option.
            cells_for_option = {}
            for option in range(1, board.n2 + 1):
                cells_for_option[option] = []

            # Count options for all cells in col.
            for row in range(board.n2):
                cell = (row, col)

                if cell in board.unsolved_cells:
                    for index, is_legal in enumerate(board.get_options(cell)):
                        if is_legal:
                            options_count[index] += 1
                            cells_for_option[index + 1].append(cell)

            # If you find an option that only had one cell as its possible location, make a move there.
            for index, count in enumerate(options_count):
                if count == 1:
                    certain_cell = cells_for_option[index + 1][0]
                    filled_cells.add(certain_cell)
                    board.make_move(certain_cell, index + 1)
                elif count > 1 and count <= board.n:
                    corresponding_cells = cells_for_option[index + 1]
                    if board.in_same_box(corresponding_cells):
                        modified_cells.union(board.remove_options_box(index, board.get_box_num(corresponding_cells[0]), col, 0))

        return (filled_cells, modified_cells)


    def deduce_boxes(self, board):
        # A collection of all filled cells.
        filled_cells = set()

        # A collection of all cells that had their options modified.
        modified_cells = set()

        for box_num in range(board.n2):
            # Counts how many cells have option (i + 1) [i is index] as a legal option.
            options_count = [0 for i in range(board.n2)]

            # Maps an option to the a list of cells that had it as a legal option.
            cells_for_option = {}
            for option in range(1, board.n2 + 1):
                cells_for_option[option] = []

            # Count options for all cells in box.
            for cell in board.get_box(box_num):
                if cell in board.unsolved_cells:
                    for index, is_legal in enumerate(board.get_options(cell)):
                        if is_legal:
                            options_count[index] += 1
                            cells_for_option[index + 1].append(cell)

            # If you find an option that only had one cell as its possible location, make a move there.
            for index, count in enumerate(options_count):
                if count == 1:
                    certain_cell = cells_for_option[index + 1][0]
                    filled_cells.add(certain_cell)
                    board.make_move(certain_cell, index + 1)
                elif count > 1 and count <= board.n:
                    corresponding_cells = cells_for_option[index + 1]
                    if board.in_same_row(corresponding_cells):
                        modified_cells.union(board.remove_options_row(index, corresponding_cells[0][0], box_num))
                    elif board.in_same_col(corresponding_cells):
                        modified_cells.union(board.remove_options_col(index, corresponding_cells[0][1], box_num))



        return (filled_cells, modified_cells)


    def find_singles(self, board):
        filled_cells = set()

        unsolved_cells = board.unsolved_cells.copy()

        for cell in unsolved_cells:
            num_options = 0
            last_option = -1

            for index, is_legal in enumerate(board.get_options(cell)):
                if is_legal:
                    num_options += 1
                    last_option = index + 1

                    if num_options > 1:
                        break

            if num_options == 1:
                board.make_move(cell, last_option)
                filled_cells.add(cell)

        return (filled_cells, set())



def test_board(board):
    for row in range(board.n2):
        vals = [0 for i in range(board.n2)]
        for col in range(board.n2):
            cell = (row, col)
            vals[board.board[cell] - 1] += 1
            if vals[board.board[cell] - 1] > 1:
                print("Error in row @ %s" % str(cell))
                return

    for col in range(board.n2):
        vals = [0 for i in range(board.n2)]
        for row in range(board.n2):
            cell = (row, col)
            vals[board.board[cell] - 1] += 1
            if vals[board.board[cell] - 1] > 1:
                print("Error in col @ %s" % str(cell))
                return

    for box_num in range(board.n2):
        vals = [0 for i in range(board.n2)]
        first_row = (box_num // board.n) * board.n
        first_col = (box_num % board.n) * board.n

        for i in range(board.n2):
            cell = (first_row + i // board.n, first_col + i % board.n)
            vals[board.board[cell] - 1] += 1
            if vals[board.board[cell] - 1] > 1:
                print("Error in box @ %s" % str(cell))
                return


if __name__ == "__main__":
    # change this to the input file that you'd like to test
    board = Board('tests/test-6-ridiculous/02.csv')
    s = Solver()
    #s.solveBoard(board)
    cProfile.run("s.solveBoard(board)", sort="tottime")
    board.print()