#include <cstdint>
#include <vector>

// Six-neighbour BFS in a C-order (x,y,z) Boolean array.
// start = -1 means seed every admissible site on x=0.
// Returned length counts edges; -1 means that x=nx-1 is unreachable.
extern "C" int face_bfs(const uint8_t* mask, int nx, int ny, int nz,
                         int start, int* parent, int* goal) {
    const int plane=ny*nz, n=nx*plane;
    std::vector<int> d(n,-1), q(n);
    int head=0,tail=0;
    if(parent) for(int i=0;i<n;++i) parent[i]=-1;
    if(start>=0) {
        if(start>=n || !mask[start]) { *goal=-1; return -1; }
        d[start]=0; q[tail++]=start;
    } else {
        for(int i=0;i<plane;++i) if(mask[i]) { d[i]=0; q[tail++]=i; }
    }
    while(head<tail) {
        int v=q[head++], x=v/plane, y=(v%plane)/nz, z=v%nz;
        if(x==nx-1) { *goal=v; return d[v]; }
        int u[6]={v-plane,v+plane,v-nz,v+nz,v-1,v+1};
        bool ok[6]={x>0,x+1<nx,y>0,y+1<ny,z>0,z+1<nz};
        for(int k=0;k<6;++k) if(ok[k] && mask[u[k]] && d[u[k]]<0) {
            d[u[k]]=d[v]+1;
            if(parent) parent[u[k]]=v;
            q[tail++]=u[k];
        }
    }
    *goal=-1;
    return -1;
}
