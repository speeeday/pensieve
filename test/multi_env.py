import numpy as np
from scheduling import fair_sharing

MILLISECONDS_IN_SECOND = 1000.0
B_IN_MB = 1000000.0
BITS_IN_BYTE = 8.0
RANDOM_SEED = 42
VIDEO_CHUNCK_LEN = 4000.0  # millisec, every time add this amount to buffer
BITRATE_LEVELS = 6
TOTAL_VIDEO_CHUNCK = 48
BUFFER_THRESH = 60.0 * MILLISECONDS_IN_SECOND  # millisec, max buffer limit
DRAIN_BUFFER_SLEEP_TIME = 500.0  # millisec
PACKET_PAYLOAD_PORTION = 0.95
LINK_RTT = 80  # millisec
PACKET_SIZE = 1500  # bytes
VIDEO_SIZE_FILE = './video_size_'

class VideoClient:
    def __init__(self):
        self.video_chunk_counter_sent = 0
        self.video_chunk_counter = 0
        self.buffer_size = 0
        self.sleep_time = 0
        self.delay = 0.0
        self.end_of_video = False
        

    def serve_chunk(self, client_num, throughput, duration, video_chunk_sizes):

        if self.end_of_video == True:
            return []
        
        records = []
        
        # check if buffer is greater than threshold, if so sleep
        if self.buffer_size > BUFFER_THRESH:
            # exceed the buffer limit
            # we need to skip some network bandwidth here
            # but do not add up the delay
            drain_buffer_time = min(self.buffer_size - BUFFER_THRESH, duration * MILLISECONDS_IN_SECOND)
            # round off to 0.5 ms
            self.sleep_time += np.ceil(drain_buffer_time / DRAIN_BUFFER_SLEEP_TIME) * \
                         DRAIN_BUFFER_SLEEP_TIME
            self.buffer_size -= self.sleep_time
            duration -= self.sleep_time / MILLISECONDS_IN_SECOND

        if duration > 0.0:
            packet_payload = throughput * duration * PACKET_PAYLOAD_PORTION

            video_chunk_size = video_chunk_sizes[self.video_chunk_counter]
            
            if self.video_chunk_counter_sent + packet_payload > video_chunk_size:
                # NEED TO PRINT OUT FRACTIONAL TIME, SEE WHY DELAY IS OFF
                
                # chunk finished being served
                fractional_time = (video_chunk_size - self.video_chunk_counter_sent) / \
                                  throughput / PACKET_PAYLOAD_PORTION
                self.delay += fractional_time
                self.video_chunk_counter_sent = 0

                duration -= np.ceil(fractional_time / DRAIN_BUFFER_SLEEP_TIME) * \
                            DRAIN_BUFFER_SLEEP_TIME
                
                return_sleep_time = self.sleep_time
                return_delay = (self.delay * MILLISECONDS_IN_SECOND) + LINK_RTT
                
                
                self.video_chunk_counter += 1
                video_chunk_remain = TOTAL_VIDEO_CHUNCK - self.video_chunk_counter


                return_end_of_video = False
                if self.video_chunk_counter >= TOTAL_VIDEO_CHUNCK:
                    self.end_of_video = True
                    return_end_of_video = True
                    self.buffer_size = 0
                    self.video_chunk_counter = 0


                # rebuffer time
                rebuf = np.maximum(return_delay - self.buffer_size, 0.0)

                # update the buffer
                self.buffer_size = np.maximum(self.buffer_size - return_delay, 0.0)

                # add in the new chunk
                self.buffer_size += VIDEO_CHUNCK_LEN

                return_buffer_size = self.buffer_size
                
                records.append((client_num, \
                                return_delay, \
                                return_sleep_time, \
                                return_buffer_size / MILLISECONDS_IN_SECOND, \
                                rebuf / MILLISECONDS_IN_SECOND, \
                                video_chunk_size, \
                                return_end_of_video, \
                                video_chunk_remain))
                    
                self.video_chunk_counter_sent = 0
                self.sleep_time = 0
                self.delay = 0

                if duration > 0.0 and not(self.end_of_video):
                    records = records + self.serve_chunk(client_num, throughput, duration, video_chunk_sizes)
                
            else:
                # start serving next chunk for the duration
                self.video_chunk_counter_sent += packet_payload
                self.delay += duration
        return records        


        

class Environment:

    NEW_CLIENT_PROB = 0.3 # tunable parameter
    MAX_CLIENT_NUM = 1     # tunable parameter        

    def __init__(self, all_cooked_time, all_cooked_bw, random_seed=RANDOM_SEED):
        assert len(all_cooked_time) == len(all_cooked_bw)

        np.random.seed(random_seed)

        self.num_clients = 1
        self.clients = [VideoClient()]

        self.all_cooked_time = all_cooked_time
        self.all_cooked_bw = all_cooked_bw

#        self.video_chunk_counter = 0
#        self.buffer_size = 0

        # pick a random trace file
        self.trace_idx = 0
        self.cooked_time = self.all_cooked_time[self.trace_idx]
        self.cooked_bw = self.all_cooked_bw[self.trace_idx]

        self.mahimahi_start_ptr = 1
        # randomize the start point of the trace
        # note: trace file starts with time 0
        self.mahimahi_ptr = 1
        self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]

        self.video_size = {}  # in bytes
        for bitrate in xrange(BITRATE_LEVELS):
            self.video_size[bitrate] = []
            with open(VIDEO_SIZE_FILE + str(bitrate)) as f:
                for line in f:
                    self.video_size[bitrate].append(int(line.split()[0]))

    def get_video_chunks(self, quality):

        assert all([q >= 0 for q in quality])
        assert all([q < BITRATE_LEVELS for q in quality])

                   
        # need to treat quality as a list instead of a bitrate value
        # change simulator to serve all clients at every timestep, and return if any clients were able to finish in their timestep
                   
        #video_chunk_size = self.video_size[quality][self.video_chunk_counter]


        # at each timestep a new client joins with random probability
        if (self.num_clients < self.MAX_CLIENT_NUM) and (np.random.random() < self.NEW_CLIENT_PROB):
            self.clients.append(VideoClient())
            self.num_clients += 1
        

        # use the delivery opportunity in mahimahi
        delay = 0.0  # in ms
        video_chunk_counter_sent = 0  # in bytes

#        while True:  # download video chunk over mahimahi
        throughput = self.cooked_bw[self.mahimahi_ptr] \
                   * B_IN_MB / BITS_IN_BYTE
        duration = self.cooked_time[self.mahimahi_ptr] \
                   - self.last_mahimahi_time

        # Scheduling policy goes here
        # Should return a weight vector that distributes traffic between clients
        weighted_queue = fair_sharing(self.num_clients)

        records = []
                   
        for c in range(self.num_clients):
            # simulate the timestep for each client given its proportion of BW
            # add any records to be logged into the records list to be returned
            video_chunk_sizes = self.video_size[quality[c]]
            records += self.clients[c].serve_chunk(c, throughput, duration, video_chunk_sizes)


        # check if all videos are done (if so, iterate traces)
        if self.num_clients == self.MAX_CLIENT_NUM and all([v.end_of_video for v in self.clients]):
            self.trace_idx += 1
            if self.trace_idx >= len(self.all_cooked_time):
                self.trace_idx = 0            

            self.cooked_time = self.all_cooked_time[self.trace_idx]
            self.cooked_bw = self.all_cooked_bw[self.trace_idx]

            # randomize the start point of the video
            # note: trace file starts with time 0
            self.mahimahi_ptr = self.mahimahi_start_ptr
            self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]

            self.num_clients = 1
            self.clients = [VideoClient()]

        else:
            self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr]
            self.mahimahi_ptr += 1

            if self.mahimahi_ptr >= len(self.cooked_bw):
                # loop back in the beginning
                # note: trace file starts with time 0
                self.mahimahi_ptr = 1
                self.last_mahimahi_time = 0


        return records
