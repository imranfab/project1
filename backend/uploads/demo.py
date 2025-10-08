def bruteforce(arr,n,target):
    for i in range(n):
        cursum=0
        for j in range(i,n):
            cursum += arr[j]
            if cursum == target:
                print(arr[i : j+1])
                
arr=list(map(int,input().split()))
target=int(input())
n=len(arr)
bruteforce(arr,n,target)
