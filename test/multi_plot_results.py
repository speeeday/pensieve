import os
import numpy as np
import matplotlib.pyplot as plt


RESULTS_FOLDER = './multi_results/'
NUM_BINS = 100
BITS_IN_BYTE = 8.0
MILLISEC_IN_SEC = 1000.0
M_IN_B = 1000000.0
VIDEO_LEN = 48
VIDEO_BIT_RATE = [300, 750, 1200, 1850, 2850, 4300]
K_IN_M = 1000.0
REBUF_P = 4.3
SMOOTH_P = 1
COLOR_MAP = plt.cm.jet #nipy_spectral, Set1,Paired 
SIM_DP = 'sim_dp'
#SCHEMES = ['BB', 'RB', 'FIXED', 'FESTIVE', 'BOLA', 'RL',  'sim_rl', SIM_DP]
#SCHEMES = ['sim_rl', SIM_DP]
SCHEMES = ['BB']
SCHEME = 'BB'

# QoE policy definitions
def max_min_fairness(l):
        return min(l)



def main():

	time_all = {}
	bit_rate_all = {}
	buff_all = {}
	bw_all = {}
	raw_reward_all = {}

	for scheme in SCHEMES:
		time_all[scheme] = {}
		raw_reward_all[scheme] = {}
		bit_rate_all[scheme] = {}
		buff_all[scheme] = {}
		bw_all[scheme] = {}

        multi_time_all = {}
	multi_bit_rate_all = {}
	multi_buff_all = {}
	multi_bw_all = {}
	multi_raw_reward_all = {}

	for scheme in SCHEMES:
		multi_time_all[scheme] = {}
		multi_raw_reward_all[scheme] = {}
		multi_bit_rate_all[scheme] = {}
		multi_buff_all[scheme] = {}
		multi_bw_all[scheme] = {}

	log_files = os.listdir(RESULTS_FOLDER)
	for log_file in log_files:

		time_ms = []
		bit_rate = []
		buff = []
		bw = []
		reward = []

		print log_file

		with open(RESULTS_FOLDER + log_file, 'rb') as f:
			if SIM_DP in log_file:
				last_t = 0
				last_b = 0
				last_q = 1
				lines = []
				for line in f:
					lines.append(line)
					parse = line.split()
					if len(parse) >= 6:
						time_ms.append(float(parse[3]))
						bit_rate.append(VIDEO_BIT_RATE[int(parse[6])])
						buff.append(float(parse[4]))
						bw.append(float(parse[5]))
				
				for line in reversed(lines):
					parse = line.split()
					r = 0
					if len(parse) > 1:
						t = float(parse[3])
						b = float(parse[4])
						q = int(parse[6])
						if b == 4:
							rebuff = (t - last_t) - last_b
							assert rebuff >= -1e-4
							r -= REBUF_P * rebuff

						r += VIDEO_BIT_RATE[q] / K_IN_M
						r -= SMOOTH_P * np.abs(VIDEO_BIT_RATE[q] - VIDEO_BIT_RATE[last_q]) / K_IN_M
						reward.append(r)

						last_t = t
						last_b = b
						last_q = q

			else:
				for line in f:
					parse = line.split()
					if len(parse) <= 1:
						break
					time_ms.append(float(parse[0]))
					bit_rate.append(int(parse[1]))
					buff.append(float(parse[2]))
					bw.append(float(parse[4]) / float(parse[5]) * BITS_IN_BYTE * MILLISEC_IN_SEC / M_IN_B)
					reward.append(float(parse[6]))
                                        print "{}\t{}\t{}\t{}\t{}".format(float(parse[0]), int(parse[1]), float(parse[2]),float(parse[4]) / float(parse[5]) * BITS_IN_BYTE * MILLISEC_IN_SEC / M_IN_B, float(parse[6])) 

		if SIM_DP in log_file:
			time_ms = time_ms[::-1]
			bit_rate = bit_rate[::-1]
			buff = buff[::-1]
			bw = bw[::-1]
		
		time_ms = np.array(time_ms)
#		time_ms -= time_ms[0]
		
		# print log_file

		for scheme in SCHEMES:
                        print "Checking if {} is in {}".format(scheme, log_file)
			if "_{}_".format(scheme.lower()) in log_file.lower():
                                print "Found!"
				multi_time_all[scheme][log_file[len('log_' + str(scheme) + '_'):]] = time_ms
				multi_bit_rate_all[scheme][log_file[len('log_' + str(scheme) + '_'):]] = bit_rate
				multi_buff_all[scheme][log_file[len('log_' + str(scheme) + '_'):]] = buff
				multi_bw_all[scheme][log_file[len('log_' + str(scheme) + '_'):]] = bw
				multi_raw_reward_all[scheme][log_file[len('log_' + str(scheme) + '_'):]] = reward
				break


        # ---- ---- ---- ----
        # Organize Rewards
        # ---- ---- ---- ----

        for scheme in SCHEMES:
                for k in multi_time_all[scheme]:
                        key = '_'.join(k.split('_')[:-2])
                        print "{} ---> {}".format(k,key)
                        if key not in time_all[scheme]:
                                time_all[scheme][key] = []
                                bit_rate_all[scheme][key] = []
                                buff_all[scheme][key] = []
                                bw_all[scheme][key] = []
                                raw_reward_all[scheme][key] = []
                        time_all[scheme][key].append(multi_time_all[scheme][k])
                        bit_rate_all[scheme][key].append(multi_bit_rate_all[scheme][k])
                        buff_all[scheme][key].append(multi_buff_all[scheme][k])
                        bw_all[scheme][key].append(multi_bw_all[scheme][k])
                        raw_reward_all[scheme][key].append(multi_raw_reward_all[scheme][k])
                        print bit_rate_all[scheme][key]
                        

        # Fix the time_all structure
        for scheme in SCHEMES:
                for k in time_all[scheme]:
                        inits = []
                        for i in range(len(time_all[scheme][k])):
#                                print time_all[scheme][k][i]
                                inits.append(time_all[scheme][k][i][0])
                        for i in range(len(time_all[scheme][k])):
                                time_all[scheme][k][i] -= min(inits)

                        
        # ---- ---- ---- ----
        # Combine Rewards
        # ---- ---- ---- ----
        for scheme in SCHEMES:
                for k in raw_reward_all[scheme]:
                        raw_reward_all[scheme][k] = max_min_fairness(raw_reward_all[scheme][k])
        
                        
	# ---- ---- ---- ----
	# Reward records
	# ---- ---- ---- ----
        print "\nReward Records"

	log_file_all = []
	reward_all = {}
	for scheme in SCHEMES:
		reward_all[scheme] = []  


        print time_all[SCHEMES[0]]

        print "Schemes Check:"
        
	for l in time_all[SCHEMES[0]]:
		schemes_check = True
		for scheme in SCHEMES:
                        print "Cond 1: {}".format(l not in time_all[scheme])

			if l not in time_all[scheme]: 
				schemes_check = False
				break
                        for i in range(len(time_all[scheme][l])):
                                print "Cond 2: {} - {}".format(len(time_all[scheme][l][i]) < VIDEO_LEN, len(time_all[scheme][l][i]))
                                if len(time_all[scheme][l][i]) < VIDEO_LEN:
                                        schemes_check = False
                                        break
		if schemes_check:
			log_file_all.append(l)
			for scheme in SCHEMES:
				reward_all[scheme].append(np.sum(raw_reward_all[scheme][l][1:VIDEO_LEN]))
                                print "{}".format(np.sum(raw_reward_all[scheme][l][1:VIDEO_LEN]))

	mean_rewards = {}
	for scheme in SCHEMES:
		mean_rewards[scheme] = np.mean(reward_all[scheme])

	fig = plt.figure()
	ax = fig.add_subplot(111)

	for scheme in SCHEMES:
		ax.plot(reward_all[scheme])
	
	SCHEMES_REW = []
	for scheme in SCHEMES:
		SCHEMES_REW.append(scheme + ': ' + str(mean_rewards[scheme]))

	colors = [COLOR_MAP(i) for i in np.linspace(0, 1, len(ax.lines))]
	for i,j in enumerate(ax.lines):
		j.set_color(colors[i])

	ax.legend(SCHEMES_REW, loc=4)
	
	plt.ylabel('total reward')
	plt.xlabel('trace index')
	plt.show()

	# ---- ---- ---- ----
	# CDF 
	# ---- ---- ---- ----

	fig = plt.figure()
	ax = fig.add_subplot(111)

	for scheme in SCHEMES:
		values, base = np.histogram(reward_all[scheme], bins=NUM_BINS)
		cumulative = np.cumsum(values)
		ax.plot(base[:-1], cumulative)	

	colors = [COLOR_MAP(i) for i in np.linspace(0, 1, len(ax.lines))]
	for i,j in enumerate(ax.lines):
		j.set_color(colors[i])	

	ax.legend(SCHEMES_REW, loc=4)
	
	plt.ylabel('CDF')
	plt.xlabel('total reward')
	plt.show()


	# ---- ---- ---- ----
	# check each trace
	# ---- ---- ---- ----

	for l in time_all[SCHEMES[0]]:
		schemes_check = True
		for scheme in SCHEMES:
                        print "Cond 1: {}".format(l not in time_all[scheme])

			if l not in time_all[scheme]: 
				schemes_check = False
				break
                        for i in range(len(time_all[scheme][l])):
                                print "Cond 2: {} - {}".format(len(time_all[scheme][l][i]) < VIDEO_LEN, len(time_all[scheme][l][i]))
                                if len(time_all[scheme][l][i]) < VIDEO_LEN:
                                        schemes_check = False
                                        break
                        
		if schemes_check:
			fig = plt.figure()

			ax = fig.add_subplot(311)
			for scheme in SCHEMES:
                                for i in range(len(time_all[scheme][l])):
                                        print time_all[scheme][l][i][:VIDEO_LEN]
                                        print bit_rate_all[scheme][l][i][:VIDEO_LEN]
				        ax.plot(time_all[scheme][l][i][:VIDEO_LEN], bit_rate_all[scheme][l][i][:VIDEO_LEN])
			colors = [COLOR_MAP(i) for i in np.linspace(0, 1, len(ax.lines))]
			for i,j in enumerate(ax.lines):
				j.set_color(colors[i])	
			plt.title(l)
			plt.ylabel('bit rate selection (kbps)')

			ax = fig.add_subplot(312)
			for scheme in SCHEMES:
                                for i in range(len(time_all[scheme][l])):
				        ax.plot(time_all[scheme][l][i][:VIDEO_LEN], buff_all[scheme][l][i][:VIDEO_LEN])
			colors = [COLOR_MAP(i) for i in np.linspace(0, 1, len(ax.lines))]
			for i,j in enumerate(ax.lines):
				j.set_color(colors[i])	
			plt.ylabel('buffer size (sec)')

			ax = fig.add_subplot(313)
			for scheme in SCHEMES:
                                for i in range(len(time_all[scheme][l])):
				        ax.plot(time_all[scheme][l][i][:VIDEO_LEN], bw_all[scheme][l][i][:VIDEO_LEN])
			colors = [COLOR_MAP(i) for i in np.linspace(0, 1, len(ax.lines))]
			for i,j in enumerate(ax.lines):
				j.set_color(colors[i])	
			plt.ylabel('bandwidth (mbps)')
			plt.xlabel('time (sec)')

			SCHEMES_REW = []
			for scheme in SCHEMES:
				SCHEMES_REW.append(scheme + ': ' + str(np.sum(raw_reward_all[scheme][l][1:VIDEO_LEN])))

			ax.legend(SCHEMES_REW, loc=9, bbox_to_anchor=(0.5, -0.1), ncol=int(np.ceil(len(SCHEMES) / 2.0)))
			plt.show()
                else:
                        print "Scheme didn't CHECK"
                                

if __name__ == '__main__':
	main()
