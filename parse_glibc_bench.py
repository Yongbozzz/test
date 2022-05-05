#!/usr/bin/python3
# Copyright (C) FIXME
'''Parse the output files of glibc-bench

'''
import os
import sys
import re
import argparse
import json

DEFAULT_GLIBC_VERSION = "2.35"
SPLIT_CH = ''
TEST_FILE_LIST = ["bench-malloc-simple*.out", "bench-malloc-thread*.out", "bench.out",
                  "bench-math-inlines.out",
                  "bench-sprintf.out", "bench-strtod.out", "bench-strcpy.out", "bench-memset.out",
                  "bench-memcpy-large.out"]


class Parser:
    '''
    Common class
    '''

    # pylint: disable=R0913
    def __init__(self, filename, target_words_list, selector_words_list=None,
                 selector_ifunc_list=None, selector_step=1,
                 glibc_version=DEFAULT_GLIBC_VERSION):
        self.filename = filename
        self.target_words_list = target_words_list
        self.selector_words_list = selector_words_list
        self.selector_ifunc_list = selector_ifunc_list
        self.selector_step = selector_step
        self.glibc_version = glibc_version
        self.results = []

    # pylint: disable=W0107
    def parse(self):
        '''
        To parse an output file
        '''
        pass

    # pylint: disable=W1514
    def print_result(self):
        '''
        for i in self.results:
            print(i[0],end=':')
            print(i[1])
        '''
        with open('res2.txt', 'a') as save_file:
            for i in self.results:
                # print(i)
                save_file.write(str(i[0])+':'+str(i[1])+'\n')
        print("Total items:", len(self.results))


class ParserType1(Parser):
    '''Typical file "bench.out", pattern is below
    {
        "timing_type": "hp_timing",
        "functions": {
        "acos": {
        "": {
            "duration": 1.61643e+09,
            "iterations": 1.59654e+08,
            "max": 51.828,
            "min": 5.338,
            "mean": 10.1246
        }   => Get obj["functions"]"acos"][""]["mean"]
        "exp2f": {
            "workload-spec2017.wrf": {
            "duration": 1.62932e+09,
            "iterations": 1.28736e+08,
            "reciprocal-throughput": 4.25576,
            "latency": 21.0568,
            "max-throughput": 2.34976e+08,
            "min-throughput": 4.74905e+07
        }   => Get obj["functions"]["exp2f"]["workload-spec2017.wrf"]["latency"]
    }
    '''

    # pylint: disable=W1514
    def parse(self):
        with open(self.filename) as json_file:
            json_objs = json.load(json_file)

        for bench_name in json_objs["functions"]:
            for sub_bench_name in json_objs["functions"][bench_name]:
                if len(set(json_objs["functions"][bench_name][sub_bench_name]) -
                       set(self.target_words_list)) == 0:
                    print("Unsupport"+"functions_"+bench_name +
                          "_"+sub_bench_name+target_words)
                for target_words in self.target_words_list:  # FIXME, this is a bug
                    if target_words in json_objs["functions"][bench_name][sub_bench_name]:
                        output_string = SPLIT_CH
                        if sub_bench_name == "":
                            output_string += bench_name + "_" + target_words
                        else:
                            output_string += bench_name+"-" + sub_bench_name + "_" + target_words
                        self.results.append((output_string,
                                             json_objs["functions"][bench_name][sub_bench_name]
                                             [target_words]))


class ParserType2(Parser):
    '''For file "bench-memset.out", pattern is below
    {
        "timing_type": "hp_timing",
        "functions": {
        "memset": {
            "bench-variant": "default",
            "ifuncs": ["generic_memset", "__memset_sse2_unaligned", "__memset_sse2_unaligned_erms",
            "__memset_erms", "__memset_avx2_unaligned", "__memset_avx2_unaligned_erms",
            "__memset_avx2_unaligned_rtm", "__memset_avx2_unaligned_erms_rtm",
            "__memset_evex_unaligned", "__memset_evex_unaligned_erms",
            "__memset_avx512_unaligned_erms", "__memset_avx512_unaligned",
            "__memset_avx512_no_vzeroupper"],
            "results": [
            {
                "length": 1,
                "alignment": 0,
                "char": -65,
                "timings": [3.57495, 4.73584, 4.16284, 9.29272, 5.46558, 5.02905, 6.76709, 6.71411,
                            5.73071, 4.35254, 3.65967, 3.05664, 5.79346]
            }, => The result is a matrix , Get obj["functions"]["memset"]["results"][i]["timings"]
    '''

    # pylint: disable=R0913
    @classmethod
    def _combine_output(cls, base_string, node, ifunc_list, target_words_list,
                        selector_words_list):
        '''combine a output
        base_string = "base_string"
        node= {
            "length": 1,
            "align1": 0,
            "align2": 32,
            "timings": [3.56616, 4.48047, ...]
        }
        ifunc_list = ["generic_memmove", "__memmove_avx_unaligned", ....]
        target_words_list = ("timings", )
        selector_words_list = ["length", "align1", "align2"]
        out=("base_string-generic_memmove-length-1-align1-0-align2-32": 3.56616, ...)
        '''
        ret_list = []
        #assert len(ifunc_list) == len(node[target_words_list[0]])
        for i, ifunc in enumerate(ifunc_list):
            key_string = base_string + SPLIT_CH + "_"
            key_string += ifunc
            for select_word in selector_words_list:
                if select_word == "dst > src":
                    str_sw = "d2s"
                else:
                    str_sw = select_word
                key_string += "-" + str_sw + "_" + str(node[select_word])
            ret_kv = (key_string, node[target_words_list[0]][i])
            ret_list.append(ret_kv)
        return ret_list

    # pylint: disable=W1514
    def parse(self):
        with open(self.filename) as json_file:
            json_objs = json.load(json_file)

        assert len(json_objs["functions"]) == 1
        #base_string = os.path.basename(self.filename)
        base_string = ""
        for bench_name in json_objs["functions"]:
            if self.selector_ifunc_list is None:
                ifunc_list = json_objs["functions"][bench_name]["ifuncs"]
            else:
                ifunc_list = self.selector_ifunc_list

            # for node in  json_objs["functions"][bench_name]["results"]:
            # get node with the certain defined step
            for i in range(0, len(json_objs["functions"][bench_name]["results"]),
                           self.selector_step):
                node = json_objs["functions"][bench_name]["results"][i]
                self.results += self._combine_output(base_string + bench_name,
                                                     node, ifunc_list, self.target_words_list,
                                                     self.selector_words_list)


class ParserType3(Parser):
    '''For file "bench-memccpy.out", pattern is below
                        generic_memccpy	memccpy
        Length   16, n   16, char 12, alignment  1/ 1:	10.5408	10.1015
        Length   16, n   16, char 23, alignment  1/ 1:	9.68109	9.39548
        Length   16, n   16, char 28, alignment  1/ 2:	9.40431	9.49431
        => The result is a matrix, Get obj Length_X_n_Y_char_Z_alignment_A_B
    A special case is "bench-strtod.out“， no alternative functions
        Input 1e308                   :	120.651
        Input 100000000e300           :	154.753
        Input 0x1p1023                :	42.8969
        Input 0x1000p1011             :	58.5537
    '''

    def _combine_output(self, base_string, nodeline, func_list):
        """
        base_string = "base_string"
        node= "Length   16, n   16, char 12, alignment  1/ 1:	10.5408	10.1015 "
        func_list = ["generic_memccpy",	"memccpy" ....]
        out=("base_string-generic_memccpy-Length-16-n-16-char-12-alignment-1-1": 10.5408, ...)
        """
        value_list = nodeline.split(":")[-1].split()
        #assert len(func_list) == len(value_list)
        context_list = nodeline.split(":")[0].split(",")

        for i, func_name in enumerate(func_list):
            key_string = base_string + SPLIT_CH + "_"
            key_string += func_name + "_"
            for context in context_list:
                key_string += "_".join(context.split())
            self.results.append(
                (key_string, float(value_list[i]))
            )

    # pylint: disable=W1514
    def parse(self):
        #base_string = os.path.basename(self.filename)
        base_string = os.path.basename(self.filename).split('.')[0][6:]
        with open(self.filename) as text_file:
            first_line = text_file.readline()
            if ":" in first_line:    # special case "bench-strcoll.out"
                func_list = [""]
            else:
                if self.selector_ifunc_list is None:
                    func_list = first_line.split()   # Firsh line of file
                else:
                    func_list = self.selector_ifunc_list
            node = text_file.readlines()
            for i in range(0, len(node), self.selector_step):
                self._combine_output(base_string, node[i], func_list)


class ParserType4(Parser):
    '''For file "bench-strcoll.out", pattern is below
        "strcoll": {
        "filelist#C": {
            "duration": 1.19673e+08,
            "iterations": 16,
            "mean": 7.47954e+06
        },
        "filelist#en_US.UTF-8": {
            "duration": 4.34272e+08,
            "iterations": 16,
            "mean": 2.7142e+07
        },
        It's not a standard json formats
        => Get obj["strcoll"]["filelist#C"]["mean"]
    '''

    # pylint: disable=W1514
    def parse(self):
        #base_string = os.path.basename(self.filename)
        base_string = ""
        with open(self.filename) as json_file:
            # first line is as '  "sprintf": {'
            first_line = json_file.readline()
            case_name = first_line.strip().split()[0].split(':')[
                0].split("\"")[1]
            # convert  '  "sprintf": {' to "sprintf"
            base_string += case_name + "_"
            # find the position of '{'
            json_start_pos = first_line.index("{")-1
            json_file.seek(json_start_pos)
            # load remaining part as a json file
            json_objs = json.load(json_file)
            for sub_bench_name in json_objs:
                for target_words in self.target_words_list:
                    if target_words in json_objs[sub_bench_name]:
                        output_string = base_string + SPLIT_CH + sub_bench_name + "_" + target_words
                        #output_string =  sub_bench_name + "_" + target_words
                        self.results.append((output_string,
                                             json_objs[sub_bench_name][target_words]))


class ParserType5(Parser):
    '''For file "bench-math-inlines.out", pattern is below
        "math-inlines": {
        "__isnan": {
            "inf/nan": {
            "duration": 9.59272e+06,
            "iterations": 2048,
            "mean": 4683
            }
        },
        "__isnan_inl": {
            "inf/nan": {
            "duration": 6.7447e+06,
            "iterations": 2048,
            "mean": 3293
            }
        },
        It's not a standard json formats
        => Get obj["strcoll"]["__isnan"]["inf/nan"]["mean"]
    '''

    # pylint: disable=W1514
    def parse(self):
        #base_string = os.path.basename(self.filename)
        base_string = ""
        with open(self.filename) as json_file:
            # first line is as '  "sprintf": {'
            first_line = json_file.readline()
            case_name = first_line.strip().split()[0].split(':')[
                0].split("\"")[1]
            # convert  '  "sprintf": {' to "sprintf"
            base_string += case_name
            # find the position of '{'
            json_start_pos = first_line.index("{")-1
            json_file.seek(json_start_pos)
            # load remaining part as a json file
            json_objes = json.load(json_file)
            for sub_bench_name in json_objes:
                for sub_bench_l2_name in json_objes[sub_bench_name]:
                    for target_words in self.target_words_list:
                        if target_words in json_objes[sub_bench_name][sub_bench_l2_name]:
                            output_string = base_string + SPLIT_CH + "_" + sub_bench_name + "_" + \
                                sub_bench_l2_name + "_" + target_words
                            self.results.append((output_string,
                                                 json_objes[sub_bench_name][sub_bench_l2_name]
                                                 [target_words]))


class ParserUnsupported(Parser):
    '''dummy parser class, just to indicate "unsupported" filename
    '''

    def parse(self):
        print("Unsupported file", self.filename)


PARSER_TYPE_MAP = {
    #   "filename": (ParserTypex, target_words_list, selector_words_list )
    "bench.out":
    (ParserType1, ("mean", "latency"), None, None, 1),
    "bench-malloc-simple.*.out":
    (ParserType1,
     ("main_arena_st_allocs_0025_time", "main_arena_st_allocs_0100_time",
      "main_arena_st_allocs_0400_time", "main_arena_st_allocs_1600_time",
      "main_arena_mt_allocs_0025_time", "main_arena_mt_allocs_0100_time",
      "main_arena_mt_allocs_0400_time", "main_arena_mt_allocs_1600_time",
      "thread_arena__allocs_0025_time", "thread_arena__allocs_0100_time",
      "thread_arena__allocs_0400_time", "thread_arena__allocs_1600_time"),
     None, None, 1),
    "bench-malloc-thread.*.out":
    (ParserType1, ("time_per_iteration",), None, None, 1),
    "bench-memset-walk":
    (ParserType2, ("timings",), ("length", "char"), None, 1),
    "bench-memset":
    (ParserType2,
     ("timings",), ("length", "alignment", "char"),
     ["erms", "avx512_unaligned", "evex_unaligned_erms", "avx2_unaligned_rtm"], 64),
    "bench-wmemset":
    (ParserType2, ("timings",), ("length", "alignment", "char"), None, 1),
    "bench-rawmemchr":
    (ParserType2, ("timings",), ("length", "alignment", "char"), None, 1),
    "bench-memcmpeq":
    (ParserType2, ("timings",), ("length",
                                 "align1", "align2", "result"), None, 1),
    "bench-memcmp":
    (ParserType2, ("timings",), ("length",
                                 "align1", "align2", "result"), None, 1),
    "bench-wmemcmp":
    (ParserType2, ("timings",), ("length",
                                 "align1", "align2", "result"), None, 1),
    "bench-memcpy-random*":
    (ParserType2, ("timings",), ("length", ), None, 1),
    "bench-memcpy-walk*":
    (ParserType2, ("timings",), ("length", "dst > src"), None, 1),
    "bench-memcpy-large":
    (ParserType2, ("timings",), ("length", "align1", "align2", "dst > src"),
     ["erms", "avx512_unaligned_erms", "evex_unaligned_erms", "avx_unaligned_rtm"], 16),
    "bench-memmove-walk":
    (ParserType2, ("timings",), ("length", "dst > src"), None, 1),
    "bench-memmove-large":
    (ParserType2, ("timings",), ("length", "align1", "align2"), None, 1),
    "bench-memmove":
    (ParserType2, ("timings",), ("length", "align1", "align2"), None, 1),
    "bench-mempcpy":
    (ParserType2, ("timings",), ("length",
                                 "align1", "align2", "dst > src"), None, 1),
    "bench-strcmp":
    (ParserType2, ("timings",), ("length", "align1", "align2"), None, 1),
    "bench-wcscmp":
    (ParserType2, ("timings",), ("length", "align1", "align2"), None, 1),
    "bench-strlen":
    (ParserType2, ("timings",), ("length", "alignment"), None, 1),
    "bench-wcslen":
    (ParserType2, ("timings",), ("length", "alignment"), None, 1),
    "bench-strncmp":
    (ParserType2, ("timings",), ("strlen", "len", "align1", "align2"), None, 1),
    "bench-wcsncmp":
    (ParserType2, ("timings",), ("strlen", "len", "align1", "align2"), None, 1),
    "bench-memccpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-memmem":
    (ParserType3, (None,), (None,), None, 1),
    "bench-memrchr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-stpcpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcpcpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-memchr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wmemchr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-stpcpy_chk":
    (ParserType3, (None,), (None,), None, 1),
    "bench-stpncpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcpncpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcasecmp":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcasestr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcat":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcscat":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strchr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcschr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strchrnul":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcsschrnul":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcpy":
    (ParserType3, (None,), (None,), ["evex", "avx2_rtm", "sse3"], 32),
    "bench-wcscpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcpy_chk":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcspn":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strncasecmp":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strncat":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcsncat":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strncpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcsncpy":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strnlen":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcsnlen":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strpbrk":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcspbrk":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strrchr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcsrchr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strsep":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strstr":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strtok":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strtod":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strspn":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcsspn":
    (ParserType3, (None,), (None,), None, 1),
    "bench-wcscspn":
    (ParserType3, (None,), (None,), None, 1),
    "bench-strcoll":
    (ParserType4, ("mean", ), (None,), None, 1),
    "bench-sprintf":
    (ParserType4, ("mean",), (None,), None, 1),
    "bench-math-inlines":
    (ParserType5, ("mean",), (None,), None, 1),
}


# pylint: disable=W0613
# pylint: disable=C0206
def create_parser(filename, glibc_version=DEFAULT_GLIBC_VERSION):
    '''Create parser object
    Parse the file, detect the file type
    return different ParserType
    '''
    for parser_type_key in PARSER_TYPE_MAP:
        if re.match(parser_type_key, os.path.basename(filename)) is not None:
            return PARSER_TYPE_MAP[parser_type_key][0](
                filename, PARSER_TYPE_MAP[parser_type_key][1],
                PARSER_TYPE_MAP[parser_type_key][2],
                PARSER_TYPE_MAP[parser_type_key][3],
                PARSER_TYPE_MAP[parser_type_key][4])
    return ParserUnsupported(filename, None)


def process_file(result_file, glibc_version):
    '''Process the glibc-bench output file
    '''
    parser = create_parser(result_file, glibc_version)
    parser.parse()
    parser.print_result()
    return parser


def process_dir(result_dir, glibc_version):
    '''Process the glibc-bench output fild fold
    '''
    parser_list = []
    for filename in os.listdir(result_dir):
        if filename in TEST_FILE_LIST:
            parser = process_file(os.path.join(
                result_dir, filename), glibc_version)
            parser_list.append(parser)
    total = 0
    for parser in parser_list:
        total += len(parser.results)
    #print("total results is", total)
    return parser_list


def main(glibc_version, result_dir, result_file):
    ''' Function main
    '''
    if result_dir is None and result_file is None:
        print("Need result fold or result file")
    if result_dir is not None:
        if os.path.isdir(result_dir):
            process_dir(result_dir, glibc_version)
        else:
            print(result_dir, "is not a fold")
            sys.exit()
    else:
        if os.path.isfile(result_file):
            process_file(result_file, glibc_version)
        else:
            print(result_file, "is not a regular file")
            sys.exit()


if __name__ == '__main__':
    app_parser = argparse.ArgumentParser(
        description='Take the output fold or single output file of glibc-bench')

    app_parser.add_argument(
        '-d', type=str, help='Output directory of glibc-bench', dest='result_dir')
    app_parser.add_argument(
        '-f', type=str, help='Output file of glibc-bench', dest='result_file')
    app_parser.add_argument('--glibc_version', default='2.35', type=str,
                            help='glibc version info, default value is "2.35"')
    args = app_parser.parse_args()
    main(args.glibc_version, args.result_dir, args.result_file)
