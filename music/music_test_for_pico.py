import TAG_music as music
import board

if __name__ == "__main__":
    ye = music.Musician([music.Piezo(board.GP17, "17"), music.Piezo(board.GP14)])
    ye.load_song_from_file("pico_Fetty.json")
    ye.play_song()