import sequence as sq

tl = sq.Timeline(1e12)
tl.show_progress = False
tl.init()
tl.run()
print("timeline ran")
