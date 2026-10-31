// OpenSSL 3.5+ ML-DSA-44 test harness, local research keys only.
#include <openssl/evp.h>
#include <openssl/core_names.h>
#include <openssl/params.h>
#include <openssl/err.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *readall(const char *path, size_t *len){
 FILE *f=fopen(path,"rb");if(!f){perror(path);exit(2);}fseek(f,0,SEEK_END);long sz=ftell(f); rewind(f);
 if(sz<0){exit(2);}unsigned char *p=malloc((size_t)sz+1); if(!p){exit(2);}if(fread(p,1,(size_t)sz,f)!=(size_t)sz){exit(2);}fclose(f);*len=(size_t)sz;return p;
}
static void save(const char *path,const unsigned char *p,size_t n){FILE*f=fopen(path,"wb");if(!f){perror(path);exit(2);}if(fwrite(p,1,n,f)!=n)exit(2);fclose(f);}
static void fail(const char *m){fprintf(stderr,"FAILED: %s\n",m);ERR_print_errors_fp(stderr);exit(2);}
static EVP_PKEY *load_key(const char *skpath,const char *pkpath){
 size_t sklen,pklen;unsigned char *sk=readall(skpath,&sklen),*pk=readall(pkpath,&pklen);
 if(sklen!=2560||pklen!=1312)fail("wrong raw key length");
 EVP_PKEY_CTX *ctx=EVP_PKEY_CTX_new_from_name(NULL,"ML-DSA-44",NULL);
 if(!ctx||EVP_PKEY_fromdata_init(ctx)<=0)fail("fromdata init");
 OSSL_PARAM params[]={OSSL_PARAM_construct_octet_string(OSSL_PKEY_PARAM_PRIV_KEY,sk,sklen),OSSL_PARAM_construct_octet_string(OSSL_PKEY_PARAM_PUB_KEY,pk,pklen),OSSL_PARAM_END};
 EVP_PKEY*p=NULL;if(EVP_PKEY_fromdata(ctx,&p,EVP_PKEY_KEYPAIR,params)<=0)fail("fromdata keypair");
 EVP_PKEY_CTX_free(ctx);free(sk);free(pk);return p;
}
static EVP_PKEY *load_public(const char *pkpath){
 size_t pklen;unsigned char *pk=readall(pkpath,&pklen);if(pklen!=1312)fail("wrong pk length");
 EVP_PKEY_CTX *ctx=EVP_PKEY_CTX_new_from_name(NULL,"ML-DSA-44",NULL);
 if(!ctx||EVP_PKEY_fromdata_init(ctx)<=0)fail("fromdata init");
 OSSL_PARAM params[]={OSSL_PARAM_construct_octet_string(OSSL_PKEY_PARAM_PUB_KEY,pk,pklen),OSSL_PARAM_END};
 EVP_PKEY*p=NULL;if(EVP_PKEY_fromdata(ctx,&p,EVP_PKEY_PUBLIC_KEY,params)<=0)fail("fromdata public");
 EVP_PKEY_CTX_free(ctx);free(pk);return p;
}
int main(int argc,char**argv){
 if(argc==4&&!strcmp(argv[1],"keygen")){
 EVP_PKEY_CTX*ctx=EVP_PKEY_CTX_new_from_name(NULL,"ML-DSA-44",NULL);EVP_PKEY*p=NULL;
 if(!ctx||EVP_PKEY_keygen_init(ctx)<=0||EVP_PKEY_keygen(ctx,&p)<=0)fail("keygen");
 unsigned char sk[2560],pk[1312];size_t sklen=0,pklen=sizeof pk;
 if(EVP_PKEY_get_octet_string_param(p,OSSL_PKEY_PARAM_PRIV_KEY,sk,sizeof sk,&sklen)<=0||sklen!=2560)fail("private export");
 if(EVP_PKEY_get_raw_public_key(p,pk,&pklen)<=0||pklen!=1312)fail("public export");
 save(argv[2],sk,sklen);save(argv[3],pk,pklen);puts("KEYGEN_OK");EVP_PKEY_free(p);EVP_PKEY_CTX_free(ctx);return 0;
 }
 if(argc==6&&!strcmp(argv[1],"sign")){
 EVP_PKEY*p=load_key(argv[2],argv[3]);size_t mlen;unsigned char*msg=readall(argv[4],&mlen),sig[2420];size_t slen=sizeof sig;
 EVP_MD_CTX*ctx=EVP_MD_CTX_new();if(!ctx||EVP_DigestSignInit_ex(ctx,NULL,NULL,NULL,NULL,p,NULL)<=0||EVP_DigestSign(ctx,sig,&slen,msg,mlen)<=0||slen!=2420)fail("sign");
 save(argv[5],sig,slen);puts("SIGN_OK");free(msg);EVP_MD_CTX_free(ctx);EVP_PKEY_free(p);return 0;
 }
 if(argc==5&&!strcmp(argv[1],"verify")){
 EVP_PKEY*p=load_public(argv[2]);size_t mlen,slen;unsigned char*msg=readall(argv[3],&mlen),*sig=readall(argv[4],&slen);
 EVP_MD_CTX*ctx=EVP_MD_CTX_new();if(!ctx||EVP_DigestVerifyInit_ex(ctx,NULL,NULL,NULL,NULL,p,NULL)<=0)fail("verify init");
 int ok=EVP_DigestVerify(ctx,sig,slen,msg,mlen);printf("VERIFY_%s\n",ok==1?"ACCEPT":"REJECT");
 free(sig);free(msg);EVP_MD_CTX_free(ctx);EVP_PKEY_free(p);return ok==1?0:1;
 }
 puts("USAGE: openssl_mldsa keygen sk.bin pk.bin | sign sk.bin pk.bin msg.txt sig.bin | verify pk.bin msg.txt sig.bin");return 2;
}
