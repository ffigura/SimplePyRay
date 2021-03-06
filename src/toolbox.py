import numpy as np
import matplotlib.pyplot as pylab
from su import *

def agc(output, window=100): #with headers
	func = agc_func(output['trace'], window)
	output['trace'] /= func
	output['trace'][~np.isfinite(output['trace'])] = 0
	return output
	
def mix(output, window=10):
	vec = np.ones(window)/(window/2.)
	func = np.apply_along_axis(lambda m: np.convolve(m, vec, mode='same'), axis=0, arr=output['trace'])
	output['trace'] *= 0
	output['trace'] += func
	return output
	

def build_wavelet(lowcut, highcut, ns=200, dt = 0.001):
	'''builds a band limited zero
	phase wavelet by filtering in the 
	frequency domain. quick and dirty - 
	i've used a smoother to reduce 
	wavelet ring
	
	use:
	low = 5. #hz
	high = 140. #hz
	wavelet = build_wavelet(low, high)
	'''
	
	signal = np.zeros(ns)
	signal[np.int(ns/2.)] = 1.0
	fft = np.fft.fft(signal)
	n = signal.size
	timestep = dt
	freq = np.fft.fftfreq(n, d=timestep)
	filter = (lowcut < np.abs(freq)) & (np.abs(freq) < highcut)
	filter = np.convolve(filter, np.ones(100, 'f')/100., mode='same')
	fft *= filter
	signal=np.fft.ifft(fft)
	return signal.real
	
class build_model(dict):
	def __init__(self,*arg,**kw):
		super(build_model, self).__init__(*arg, **kw)
		self['nlayers'] = 5
		self['nx'] = 500
		fault_throw = 20
		
		self['dz'] = np.array([40, 80, 40, 200, 400, ])
		self['vp'] = np.array([800., 2200., 1800., 2400., 4500., ])
		self['vs'] = self['vp']/2.
		self['rho'] = np.array([1500., 2500., 1400., 2700., 4500., ])
		self['depths'] = np.cumsum(self['dz'])
		
		self['model'] = {}
		for model in ['vp', 'vs', 'rho']:
			layer_list = []
			for index in range(self['nlayers']):
				layer = np.ones((self['nx'], self['dz'][index]), 'f')
				layer *= self[model][index]
				layer_list.append(layer)
			self['model'][model] = np.hstack(layer_list)
			self['model'][model][250:500,120:160] = self[model][1]
			self['model'][model][250:500,120+fault_throw:160+fault_throw] = self[model][2]
		
		self['model']['z'] = self['model']['vp'] * self['model']['rho']
		self['model']['R'] = (np.roll(self['model']['z'], shift=-1) - self['model']['z'])/(np.roll(self['model']['z'], shift=-1) + self['model']['z'])
		self['model']['R'][:,0] *= 0
		self['model']['R'][:,-1:] *= 0
		self['model']['R'][:,:self['dz'][0]+2] = 0
		
		
	#def __repr__(self):
		#return repr(self['model'])
			
	def display(self):
		for m in self['model'].keys():
			pylab.figure()
			pylab.imshow(a['model'][m].T)
			pylab.colorbar()
			pylab.xlabel('m')
			pylab.ylabel('m')
			pylab.title(m)
		pylab.show()
		
def agc_func(data, window):
    vec = np.ones(window)/(window/2.)
    func = np.apply_along_axis(lambda m: np.convolve(np.abs(m), vec, mode='same'), axis=-1, arr=data)
    return func
    
def find_points(x0, z0, x1, z1, nump, model):
	'''
	nearest neighbour search
	'''
	
	x = np.linspace(x0, x1, nump, endpoint=False)
	z = np.linspace(z0, z1, nump, endpoint=False) #generate rays
	xint = np.ceil(x) #round em down
	zint = np.ceil(z) #round em down
	return model[xint.astype(np.int), zint.astype(np.int)] 

def traveltime(x0, z0, x1, z1, model, nump, ds):
	x = np.linspace(x0, x1, nump, endpoint=False)
	z = np.linspace(z0, z1, nump, endpoint=False) #generate rays
	xint = np.ceil(x) #round em down
	zint = np.ceil(z) #round em down
	vel_points = model[xint.astype(np.int), zint.astype(np.int)] 
	return np.sum(ds/vel_points)
	
def roll(input, shift):
	input = np.pad(input, shift, mode='reflect') #pad to get rid of edge effect
	output = np.roll(input, shift=shift) #shift the values by 1
	return output[shift:-1*shift]
	
def conv(output, wavelet):
	return np.apply_along_axis(lambda m: np.convolve(m, wavelet, mode='same'), axis=1, arr=output)
	
def build_supergather(step, width, bins, dataset):
	sutype = np.result_type(dataset)
	cdps = np.unique(dataset['cdp'])
	dataset['offset'] = np.abs(dataset['offset'])
	supergather_centres = range(min(cdps)+width, max(cdps)-width, step)
	supergather_slices = [cdps[a-width:a+width] for a in supergather_centres]
	for index, inds in enumerate(supergather_slices):
		for cdpn, cdp in enumerate(dataset['cdp']):
			if cdp in inds:
				dataset['ns1'][cdpn] = index
				
	dataset = dataset[dataset['ns1'] != 0]
	output = np.empty(0, dtype=sutype)
	for ind in np.unique(dataset['ns1']):
		sg = dataset[dataset['ns1'] == ind]
		hist = np.digitize(sg['offset'], bins)
		sg['ep'] = hist
		vals = np.unique(sg['ep'])
		holder = np.zeros(len(vals), dtype=sutype)
		for v in vals:
			traces = sg[sg['ep'] == v]
			header = traces[0].copy()
			header['trace'].fill(0.0)
			fold = traces.size
			header['trace'] += np.sum(traces['trace'], axis=-2)/np.float(fold)
			holder[v-1] = header
		#~ display(holder)		
		output = np.concatenate([output, holder])
		
	return output
	