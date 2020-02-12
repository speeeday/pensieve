import numpy as np
import fixed_env as env
import load_trace


S_INFO = 6  # bit_rate, buffer_size, next_chunk_size, bandwidth_measurement(throughput and time), chunk_til_video_end
S_LEN = 8  # take how many frames in the past
A_DIM = 6
VIDEO_BIT_RATE = [300,750,1200,1850,2850,4300]  # Kbps
M_IN_K = 1000.0
REBUF_PENALTY = 4.3  # 1 sec rebuffering -> 3 Mbps
SMOOTH_PENALTY = 1
DEFAULT_QUALITY = 1  # default video quality without agent
RANDOM_SEED = 42
RAND_RANGE = 1000000
RESEVOIR = 5  # BB
CUSHION = 10  # BB
SUMMARY_DIR = './results'
LOG_FILE = './results/log_sim_bb'
# log in format of time_stamp bit_rate buffer_size rebuffer_time chunk_size download_time reward


def main():

    np.random.seed(RANDOM_SEED)

    assert len(VIDEO_BIT_RATE) == A_DIM

    
    all_cooked_time, all_cooked_bw, all_file_names = load_trace.load_trace()

    net_env = env.Environment(all_cooked_time=all_cooked_time,
                              all_cooked_bw=all_cooked_bw)

    max_clients = net_env.MAX_CLIENT_NUM
    
    log_files = [None] * max_clients
    for i in range(max_clients):
        log_path = LOG_FILE + '_' + all_file_names[net_env.trace_idx] + '_client_' + str(i)
        log_file = open(log_path, 'wb')
        log_files[i] = log_file
        

    epoch = 0
    time_stamp = 0

    last_bit_rate = [DEFAULT_QUALITY] * max_clients
    bit_rate = [DEFAULT_QUALITY] * max_clients
    r_batch = [[]] * max_clients

    video_count = 0

    end_of_videos = [False] * max_clients

    while True:  # serve video forever
        # the action is from the last decision
        # this is to make the framework similar to the real
        
        chunk_info = net_env.get_video_chunk(bit_rate)

        for i in chunk_info:
            (client_num, delay, sleep_time, buffer_size, rebuf, \
             video_chunk_size, next_video_chunk_sizes, \
             end_of_video, video_chunk_remain) = i

            time_stamp += delay  # in ms
            time_stamp += sleep_time  # in ms

            # reward is video quality - rebuffer penalty
            reward = VIDEO_BIT_RATE[bit_rate] / M_IN_K \
                     - REBUF_PENALTY * rebuf \
                     - SMOOTH_PENALTY * np.abs(VIDEO_BIT_RATE[bit_rate] -
                                               VIDEO_BIT_RATE[last_bit_rate]) / M_IN_K
            r_batch[client_num].append(reward)

            last_bit_rate[client_num] = bit_rate

            # log time_stamp, bit_rate, buffer_size, reward
            log_files[client_num].write(str(time_stamp / M_IN_K) + '\t' +
                                        str(VIDEO_BIT_RATE[bit_rate]) + '\t' +
                                        str(buffer_size) + '\t' +
                                        str(rebuf) + '\t' +
                                        str(video_chunk_size) + '\t' +
                                        str(delay) + '\t' +
                                        str(reward) + '\n')
            log_files[client_num].flush()

            if buffer_size < RESEVOIR:
                bit_rate[client_num] = 0
            elif buffer_size >= RESEVOIR + CUSHION:
                bit_rate[client_num] = A_DIM - 1
            else:
                bit_rate[client_num] = (A_DIM - 1) * (buffer_size - RESEVOIR) / float(CUSHION)
            bit_rate[client_num] = int(bit_rate)

            end_of_videos[client_num] = end_of_video
            
        if all(end_of_videos):
            for client in range(max_clients):
                log_file = log_files[client]
                log_file.write('\n')
                log_file.close()

            last_bit_rate = [DEFAULT_QUALITY] * max_clients
            bit_rate = [DEFAULT_QUALITY] * max_clients
            r_batch = [[]] * max_clients

            print "video count", video_count
            video_count += 1

            if video_count > len(all_file_names):
                break

            log_files = [None] * max_clients
            for i in range(max_clients):
                log_path = LOG_FILE + '_' + all_file_names[net_env.trace_idx] + '_client_' + str(i)
                log_file = open(log_path, 'wb')
                log_files[i] = log_file

print "Done."
                
if __name__ == '__main__':
    main()
