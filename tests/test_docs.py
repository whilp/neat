import doctest

def skip_additional_tests():
    return doctest.DocFileSuite("../docs/index.txt")
