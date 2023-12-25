# -*- coding: utf-8 -*-
"""contents_maker.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xjeL6QHiKx-YvWx4wTwKVVgVKyxGkxVs

광고 사진을 만드는 코드입니다.  
과정은 다음과 같습니다.
1. chatGPT: 아이디어(input)->__마케팅 그림 묘사문__, 키워드
2. Stable Diffusion: 키워드->__그림__
3. Output: 그림(images)+묘사문(sentence)
"""
import torch
from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler
from safetensors.torch import load_file
from collections import defaultdict
from PIL import Image

def load_lora_weights(pipeline, checkpoint_path, multiplier, device, dtype):
    LORA_PREFIX_UNET = "lora_unet"
    LORA_PREFIX_TEXT_ENCODER = "lora_te"
    # load LoRA weight from .safetensors
    state_dict = load_file(checkpoint_path, device=device)

    updates = defaultdict(dict)
    for key, value in state_dict.items():
        # it is suggested to print out the key, it usually will be something like below
        # "lora_te_text_model_encoder_layers_0_self_attn_k_proj.lora_down.weight"

        layer, elem = key.split('.', 1)
        updates[layer][elem] = value

    # directly update weight in diffusers model
    for layer, elems in updates.items():

        if "text" in layer:
            layer_infos = layer.split(LORA_PREFIX_TEXT_ENCODER + "_")[-1].split("_")
            curr_layer = pipeline.text_encoder
        else:
            layer_infos = layer.split(LORA_PREFIX_UNET + "_")[-1].split("_")
            curr_layer = pipeline.unet

        # find the target layer
        temp_name = layer_infos.pop(0)
        while len(layer_infos) > -1:
            try:
                curr_layer = curr_layer.__getattr__(temp_name)
                if len(layer_infos) > 0:
                    temp_name = layer_infos.pop(0)
                elif len(layer_infos) == 0:
                    break
            except Exception:
                if len(temp_name) > 0:
                    temp_name += "_" + layer_infos.pop(0)
                else:
                    temp_name = layer_infos.pop(0)

        # get elements for this layer
        weight_up = elems['lora_up.weight'].to(dtype)
        weight_down = elems['lora_down.weight'].to(dtype)
        alpha = elems['alpha']
        if alpha:
            alpha = alpha.item() / weight_up.shape[1]
        else:
            alpha = 1.0

        # update weight
        if len(weight_up.shape) == 4:
            curr_layer.weight.data += multiplier * alpha * torch.mm(weight_up.squeeze(3).squeeze(2), weight_down.squeeze(3).squeeze(2)).unsqueeze(2).unsqueeze(3)
        else:
            curr_layer.weight.data += multiplier * alpha * torch.mm(weight_up, weight_down)

    return pipeline

def img_grid(imgs, rows=2, cols=3):
    assert len(imgs) == rows*cols

    w, h = imgs[0].size
    grid = Image.new('RGB', size=(cols*w, rows*h))
    
    for i, img in enumerate(imgs):
        grid.paste(img, box=(i%cols*w, i//cols*h))
    return grid

class imageGen:
    def __init__(self,input:str):
        self.input=input
        repo_id="SG161222/Realistic_Vision_V2.0"
        scheduler = DPMSolverMultistepScheduler.from_pretrained(repo_id, subfolder="scheduler")
        pipeline=DiffusionPipeline.from_pretrained(repo_id, scheduler=scheduler, torch_dtype=torch.float16).to("cuda")
        pipeline.enable_xformers_memory_efficient_attention()
        self.pipeline=pipeline

    def design(self):
        pipeline=self.pipeline
        load_lora_weights(pipeline, 
                          checkpoint_path="logo_v1-000012.safetensors", 
                          multiplier=0.35, 
                          device='cuda', 
                          dtype=torch.float16)
        pos="(masterpiece:1.2), best quality, high resolution, logo, 2d, white background, simple background"
        neg="(worst quality, low quality:1.4), 3d"
        images = pipeline(num_inference_steps=30, 
                          prompt=pos+','+self.input,
                          negative_prompt=neg,
                          guidance_scale=8,
                          num_images_per_prompt=6).images
        return images
    
    def ad(self):
        pipeline=self.pipeline
        pos="masterpiece, best quality, raw photo, extremely detailed skin, extremely detailed face, 8k uhd, \
            dslr, soft lighting,  film grain, Fujifilm XT3, instagram, realstic, clothes"
        neg="(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime, mutated hands and fingers:1.4), \
            (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, \
                disconnected limbs, mutation, mutated, ugly, disgusting, amputation,\
                    (nsfw:2), (sexual content:2), (nude:2), (topless:2)"
        images = pipeline(num_inference_steps=30, 
                          prompt=pos+','+self.input,
                          negative_prompt=neg,
                          guidance_scale=8,
                          num_images_per_prompt=6).images
        return images

# class post_process():
#     def __init__(self,image,sentence):
#         def image_grid(imgs, rows=2, cols=4):
#             assert len(imgs) == rows*cols

#             w, h = imgs[0].size
#             grid = Image.new('RGB', size=(cols*w, rows*h))
            
#             for i, img in enumerate(imgs):
#                 grid.paste(img, box=(i%cols*w, i//cols*h))
#             return grid
#         self.image=image
#         self.grid=image_grid(image)
#         self.sentence=sentence
        
#     def returns(self):
#         return self.grid

#     def show(self):
#         self.grid.show()
#         print(self.sentence)